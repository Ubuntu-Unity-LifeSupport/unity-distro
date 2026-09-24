# The shutdown path: known issues #2 and #6

Measured on target, boot 2026-09-23 20:44:50: snapshot Clean-updated-2026-09-23
plus libsystemd-dev, xdotool and light-locker 1.8.0-3ubuntu4+unity2, none of
which touch the session manager or Unity's shutdown code.

## #6, the double confirmation dialog - reproduced, mechanism proven

Session indicator -> "Выключение..." -> Unity's dialog ("До скорой встречи,
Mike") -> click "Выключить" -> a **second** dialog, "Выключить систему
сейчас?". Screenshot `2026-09-23-double-shutdown-dialog.png`. The machine does
not shut down; the second dialog waits.

The chain, each link measured:

1. **Unity 7 draws the first dialog itself** and, on confirmation, calls
   `org.gnome.SessionManager.Shutdown()`. Captured with `dbus-monitor`:

       method call sender=:1.85 -> destination=:1.49
         path=/org/gnome/SessionManager; interface=org.gnome.SessionManager; member=Shutdown

   `:1.85` is compiz, pid 2445; `:1.49` is `cinnamon-session-binary`, pid 1951.
   In the source, `GnomeManager::Shutdown()` in
   `UnityCore/GnomeSessionManager.cpp` sets `pending_action_ = SHUTDOWN` and
   makes that call.
2. **`org.gnome.SessionManager` is owned by cinnamon-session**, which
   implements the GNOME interface for compatibility.
3. **In cinnamon-session, `Shutdown()` means "show a dialog".**
   `csm_manager_shutdown()` calls `show_shutdown_dialog()` unconditionally;
   `logout-prompt` is not consulted on this path. The no-dialog variant is
   `RequestShutdown()` -> `request_shutdown()`.
4. **cinnamon-session asks the Cinnamon shell for the dialog, not Unity.**
   `show_end_session_dialog()` calls `ShowEndSessionDialog` on `org.Cinnamon`,
   `/org/Cinnamon`. Under Unity there is no Cinnamon shell, the call fails,
   and it falls back to its own GTK dialog - `cinnamon-session-quit`, the
   second dialog. *(Corrected 2026-09-24: the error is `ServiceUnknown`, not
   `NAME_HAS_NO_OWNER` as first written. The proxy is created without
   `DO_NOT_AUTO_START`, so the bus tries to activate `org.Cinnamon` and finds
   no service file. The journal says so on every shutdown: `CRITICAL: Failed
   to launch Cinnamon's end session dialog ... ServiceUnknown`.)*
5. **Unity is ready for a handshake that never comes.** Unity implements
   `org.gnome.SessionManager.EndSessionDialog` - gnome-session's protocol for
   asking the shell to show the end-session dialog, where Unity, seeing its own
   `pending_action_`, would confirm silently. Verified registered on compiz's
   connection. cinnamon-session never calls it.

Under gnome-session, for which Unity 7 was written, that handshake is what
prevented a second dialog. Under cinnamon-session nothing replaces it.

**The release-note workaround** -
`gsettings set com.canonical.indicator.session suppress-logout-restart-shutdown true`
(the other four keys it lists are already their defaults) - suppresses
**Unity's** dialog and keeps cinnamon's. It removes the symptom by removing
Unity's own dialog.

A startup warning in the journal, `Can't register object
'org.gnome.SessionManager.EndSessionDialog' yet as we don't have a connection,
waiting for it...`, is transient: the object is registered moments later. Not
a cause.

## #2, the menu stops responding after cancelling - reproduced

The release note says "shutdown/logout menu not working after cancelling". On
2026-09-22 cancelling **Unity's** dialog did not reproduce it. The precondition
is cancelling the **second** dialog:

1. session indicator -> "Выключение..." -> Unity's dialog
2. confirm with "Выключить"
3. cancel cinnamon-session's "Выключить систему сейчас?" (Escape)
4. session indicator -> "Выключение..." again: **nothing opens.**

`2026-09-23-shutdown-menu-stuck.png` shows the menu opening normally and no
dialog after choosing "Выключение...".

**Correction, same day: an earlier line here claimed the state was persistent
("two further attempts, zero dialogs each time"). That claim is withdrawn.** It
counted dialogs by X window name, and Unity's dialog is not an X window at all:
it is a `nux` BaseWindow drawn inside compiz, so `xdotool` can never find it.
The count could only ever be zero. Only screenshots are evidence here.

A later run of five steps then showed no Unity dialog even on the first click,
which the simple theory below does not explain - but by then the session had
been through five consecutive tests and its state was unknown. Conclusions
wait for a clean session.

**What the menu actually calls**, captured on the bus: the session indicator
does not ask Unity to show a dialog through `com.canonical.Unity.Session`; it
calls Unity's `org.gnome.SessionManager.EndSessionDialog.Open` directly - the
same entry point gnome-session would use. In `OnShellMethodCall("Open")`:

    if (pending_action_ == NONE)        -> show Unity's dialog
    else if (pending_action_ == action) -> ConfirmShutdown(); ClosedDialog();  (no dialog)

`pending_action_` is set by `GnomeManager::Shutdown()` and nothing on the
cinnamon-session side ever resolves it, so a later `Open` can take the second
branch and silently "confirm" a shutdown nobody carries out. `ConfirmShutdown()`
resets it to `NONE`, which would predict only one swallowed click - that
prediction is what the clean re-test has to check.

`InteractiveMode()` reads `com.canonical.indicator.session
suppress-logout-restart-shutdown` - the release-note workaround key. When it is
true, `Open` skips the dialog and confirms at once by design. Unity registers
its handler under the bus name `org.gnome.Shell`, which is where gnome-session
looks and cinnamon-session does not.

**Hypothesis, not yet proven:** #2 and #6 are one mechanism. After step 2 Unity
holds `pending_action_ = SHUTDOWN` and waits for the end-session handshake;
cinnamon-session's cancel in step 3 never reaches Unity, so Unity's state is
left pending and later requests are dropped. The code path in Unity that drops
them has not been found yet.

## Fix directions - not decided

- **Unity**, when the session manager is not gnome-session, calls
  `RequestShutdown()` / `RequestReboot()` after its own confirmation, since in
  cinnamon-session those skip the dialog. Keeps Unity's native dialog, which
  the workaround throws away.
- **cinnamon-session**, when the Cinnamon shell is absent, tries the shell's
  `org.gnome.SessionManager.EndSessionDialog` before falling back to GTK. That
  restores the handshake Unity was written for, and would likely fix #2 too.
- Which one is right is a question for the team as much as for us: it decides
  whether the fix belongs to Unity or to the Cinnamon layer Ubuntu Unity now
  depends on.


---

# #2 explained: an action mismatch nobody resolves

Clean session, boot 2026-09-23 21:37:14, screenshots at every step
(`2026-09-23-shutdown-path-clean-run.png`, left to right):

| Step | Screen |
|---|---|
| A. session menu -> "Выключение..." | Unity's dialog, "До скорой встречи, Mike" |
| B. "Выключить" in it | cinnamon-session's dialog - #6 again |
| C. Escape in cinnamon's dialog | desktop |
| D. "Выключение..." again | **nothing** |
| E. "Выключение..." once more | **nothing** |

**Persistent after all** - more than one request is swallowed, which rules out
the one-click theory above.

The cause is a number. Unity's action enum
(`UnityCore/GnomeSessionManagerImpl.h`):

    LOGOUT = 0, SHUTDOWN = 1, REBOOT = 2, NONE = 3

The session menu opens the dialog with action **2**, captured on the bus:

    member=Open   uint32 2   uint32 0   uint32 0   array []

- **A.** `Open(2)` with `pending_action_ == NONE`: Unity shows its dialog.
- **B.** The power button in that dialog calls `GnomeManager::Shutdown()`,
  which sets **`pending_action_ = SHUTDOWN (1)`** and calls cinnamon-session,
  which shows its own dialog.
- **C.** Cancelling cinnamon's dialog never reaches Unity. `pending_action_`
  stays 1.
- **D, E, and every later click.** `Open(2)` arrives. `pending_action_` is 1:
  not `NONE`, so no dialog; not equal to 2, so no confirmation either. The
  handler has no `else`, so the request is dropped - and `pending_action_` is
  never reset, so every later request is dropped too. The menu is dead until
  the session restarts.

This also explains why 2026-09-22 did not reproduce it: cancelling **Unity's**
dialog goes through `CancelAndHide()` -> `CancelAction()`, which resets
`pending_action_`. Only confirming Unity's dialog and then cancelling the
session manager's leaves it set.

## #2 and #6 have one root

cinnamon-session does not take part in the end-session handshake Unity 7 was
written for. For #6 that means Unity's confirmation is followed by cinnamon's
own dialog. For #2 it means a cancelled shutdown leaves Unity waiting forever,
and a request that does not match what it is waiting for is silently dropped.

## Fix, refined

**For #2, in Unity, small and local.** In `OnShellMethodCall("Open")`, a
request whose action differs from the pending one should not be dropped: the
pending action is stale - the session manager showed its own dialog and it was
cancelled - so cancel it and treat the new request as fresh. This fixes #2 on
its own, whatever the session manager, and changes nothing under gnome-session,
where the pending window is momentary because gnome-session answers at once.

**For #6, still open.** Either Unity asks cinnamon-session for the no-dialog
variants (`RequestShutdown` / `RequestReboot`) after its own confirmation, or
cinnamon-session learns to call the shell's
`org.gnome.SessionManager.EndSessionDialog` on `org.gnome.Shell` when the
Cinnamon shell is absent. The second restores the handshake Unity expects and
would fix #2 as well; the first keeps the change inside Unity. A question for
the team as much as for us.

## Did cinnamon-session ever call `org.gnome.Shell`? No

Checked before writing any code for #6, because the answer decides how a
cinnamon-session change would be described. Source:
`git clone https://github.com/linuxmint/cinnamon-session`, HEAD `06c8582`
(6.7.5-unstable, 2026-09-22), and `apt source gnome-session` (50.1) for
comparison.

`git log -S "org.gnome.Shell"` finds two commits, both on the day of the fork:

| commit | date | what happened to the shell call |
|---|---|---|
| `ced663a` Initial commit | 2013-06-02 | a copy of gnome-session: `gsm-shell.c`, `SHELL_NAME "org.gnome.Shell"` |
| `53d2cda` Rename cinnamon-session | 2013-06-02 | renamed wholesale to `org.cinnamon.Shell` / `org.cinnamon.SessionManager.EndSessionDialog` - no fallback kept |
| `38d042a` Remove gnome-shell stuff we don't use | 2013-06-04 | `csm-shell.c` deleted; `csm-manager.c` always takes `end_session_or_show_fallback_dialog` |
| `b177ab0` #177 | 2024-11-27 | new: `org.Cinnamon.ShowEndSessionDialog`, GTK dialog as fallback |

No tag contains `ced663a` without `53d2cda`; the first tag with either is
1.9.2. So **no released cinnamon-session ever called `org.gnome.Shell`**. The
inherited call was renamed the day the fork was made and deleted two days
later, in a commit whose title says why: Cinnamon did not use it. From 1.9.2
to 6.3 the session manager always showed its own GTK dialog; since 6.4.0 it
asks Cinnamon first.

**This is not a regression, and must not be described as one.** A fallback to
`org.gnome.Shell` would be a new capability: letting cinnamon-session use the
end-session dialog of any shell that implements the gnome-session protocol,
which gnome-session 50.1 still calls exactly as in 2013 (`gsm-shell.c`,
`org.gnome.Shell` at `/org/gnome/SessionManager/EndSessionDialog`).

Other things checked on the way:

- **Upstream has not touched this code since our version.**
  `show_end_session_dialog`, `launch_cinnamon_dialog` and `launch_gtk_dialog`
  are byte-identical between tag 6.4.2 (what 26.04 ships) and HEAD. A patch
  against 6.4.2 applies to master as is.
- **Timeouts are handled, the same way as absence.** `launch_cinnamon_dialog`
  is a synchronous call with timeout `-1` (the D-Bus default, 25 s). A timeout
  is not `NAME_HAS_NO_OWNER`, so it takes the other branch: `g_critical`, then
  the GTK dialog. That is the "Timeout was reached" line in the Linux Mint
  forum thread the host found. Their shell exists and answered late; ours does
  not exist and the error is immediate. Same fallback, different cause.
  *(Corrected 2026-09-24: ours is `ServiceUnknown`, which takes the same
  `g_critical` branch as their timeout - not the `g_debug` one, as this
  paragraph and the message to the host session implied. The rest stands.)*
- **Nothing in the history mentions Unity or gnome-shell as a partner** after
  2013 (`git log -i --grep` for unity / gnome-shell): only the 2013 removals
  and a 2015 workaround for Ubuntu's overlay-scrollbar.

## The same stale action restarts the machine - and the fix

Measured 2026-09-23 while checking the limitation the first fix admitted to.
Evidence: `docs/upstream/unity-stale-pending-action/evidence/08`, `09`, `12`,
`13`.

The session menu's "Выключение..." asks Unity for the **restart** dialog,
`Open(2)`, deliberately (indicator-session `my_power_off`:
`END_SESSION_TYPE_REBOOT`, "the latter adds lock & logout options in Unity").
indicator-session also connects `ConfirmedReboot`/`ConfirmedShutdown`/
`ConfirmedLogout` to its own `reboot_now`/`power_off_now`/`logout_now`, which
call logind.

So with pending `REBOOT` - "Перезагрузить" chosen in Unity's dialog,
cinnamon-session's dialog cancelled - the next "Выключение..." matches the
pending action. Unity confirms without showing anything, and indicator-session
restarts the machine:

    Open(2)         indicator -> compiz
    ConfirmedReboot compiz, 35 ms later
    login1.Reboot   system bus, 6 ms after that

Fix, `unity +unity2`: only the owner of `org.gnome.SessionManager` confirms a
pending action; any other `Open`, or one for a different action, cancels the
stale action and is handled as new. Both symptoms verified fixed on target.

# #6: options A and B, measured

2026-09-24, on target (`Clean-updated-2026-09-23` plus our packages, as
listed in each run's `steps`), unity `+unity2` in every run except B.
Runs in [`option-runs/`](option-runs/): `steps` (what was done, when, and
whether the session manager said it was running), both bus logs, and a strip
of screenshots. The inhibitor is a Python client holding
`org.gnome.SessionManager.Inhibit(..., flags=1 logout)`.

- **A** - [`option-a-cinnamon-session.patch`](option-a-cinnamon-session.patch),
  cinnamon-session `6.4.2-1+optA2`: when `org.Cinnamon` is absent and
  `org.gnome.Shell` owns the EndSessionDialog, cinnamon-session enters the
  query phase and then calls the shell's `Open` with its inhibitors, and acts
  on `Confirmed*`/`Canceled` - a port of gnome-session's
  `end_session_or_show_shell_dialog`. `+optA1` did nothing: it checked for
  `NAME_HAS_NO_OWNER`, and the real error is `ServiceUnknown` (see the
  correction above).
- **B** - [`option-b-unity.diff`](option-b-unity.diff), unity
  `+unity2+optb1`: after its own dialog, Unity calls `RequestShutdown` /
  `RequestReboot` instead of `Shutdown` / `Reboot`. In cinnamon-session that
  is exactly what the GTK dialog's button does; in gnome-session 50.1 both are
  plain aliases (`gsm_manager_request_shutdown` returns
  `gsm_manager_shutdown`), so nothing changes there.

| | today (`base`) | B | A |
|---|---|---|---|
| menu -> restart, no inhibitor | two dialogs | **one**, restart 60 ms after `RequestReboot` | **one**, restart 80 ms after `Reboot` |
| power key | cinnamon's GTK dialog | same (path unchanged) | **Unity's dialog** - lock, suspend, restart, shut down |
| power key, inhibitor | GTK dialog; inhibitors listed after confirming - by code, the same dialog as the menu row; not measured | same as today, by code - not measured | Unity's dialog says "у вас открыты файлы, которые можно сохранить" |
| menu -> restart, inhibitor | cinnamon's second dialog **lists the inhibitor**, Cancel / Ignore | **nothing shown, session stuck** (`IsSessionRunning` false); the next attempt gets `NotInRunning`, Unity falls back to **logind `Reboot` - inhibitor bypassed** | restarts at once, **inhibitor ignored** |
| cancel from the dialog | back to running | - | back to running (checked both with and without inhibitor) |
| change | - | 2 lines in Unity; existing unit tests expect `Shutdown`/`Reboot` and would change | ~190 lines in cinnamon-session - a feature for Linux Mint upstream, or ours to carry |

What the numbers say:

- **B alone is not acceptable.** It removes the second dialog by removing
  the only thing that shows inhibitors on the menu path, and cinnamon-session
  has no dialog to report them to: it stays in the query phase until someone
  answers, and Unity's fallback then restarts through logind directly. A
  user with unsaved work gets nothing the first time and loses it the second.
- **A does what gnome-session does**, and that includes gnome-session's gap:
  Unity confirms its own pending action whether or not the `Open` carries
  inhibitors (`OnShellMethodCall`, the `pending_action_ == action` branch), and
  the indicator's `Open` never carries any. Under A the inhibitor is shown on
  the power-key path but ignored on the menu path. That is a Unity behaviour,
  not A's: fix it in Unity - confirm only when the `Open` has no inhibitors,
  otherwise show the inhibitor dialog - and A covers both paths.
- A also gives the power key Unity's own dialog instead of a GTK one - one
  look for every way to shut down.
- Today's double dialog has one real merit: it is the only configuration
  that shows inhibitors on the menu path. Whatever replaces it must keep that.

**Recommendation: A, plus the Unity inhibitor fix, measured together before
anything is proposed.** A goes to Linux Mint as a feature request with our case
only (rule already recorded); until they take it, we carry it as
cinnamon-session `+unity1`.

Found on the way, not part of either option:

- `close_end_session_dialog()` calls `g_variant_unref (ret)` on `NULL` when
  `org.Cinnamon` is absent - a GLib CRITICAL on every cancel. Harmless,
  upstream, and hit by A on every cancel.
- The journal line `CRITICAL: Failed to launch Cinnamon's end session dialog`
  on every shutdown under Unity is the `ServiceUnknown` case, not an error in
  the usual sense.

# Option A with the Unity inhibitor fix - and a compiz exit race

2026-09-24, target, cinnamon-session `6.4.2-1+unity1` (option A plus a patch
that stops two CRITICALs per cancel) and unity `+unity4`. Run in
[`option-runs/unity4-optA/`](option-runs/unity4-optA/).

**Unity, two fixes** (branch `wip/confirm-inhibitors`):

1. `GnomeSessionManager`: a pending action is confirmed straight away only if
   the last dialog shown listed the inhibitors, or there are none; otherwise
   the inhibitor dialog is shown, and confirming it asks the session manager
   again. Dismissing a dialog forgets what it showed. Three new unit tests;
   51/51 with the fix, two fail without it (twice each).
2. `SessionController::Show()` ignored a request arriving while the view was
   fading out after a button press - exactly when the session manager's
   inhibitor `Open` lands (25 ms after the click). `+unity3` had fix 1 only,
   and on target it left the session waiting in the query phase with nothing
   on screen (`option-runs/unity3-optA/`). One new controller test, fails
   without the fix.

**Measured with `+unity4`:** power key -> Unity's dialog; power key with an
inhibitor -> Unity's "у вас открыты файлы"; **menu -> restart with an
inhibitor -> Unity now shows the inhibitor warning** instead of restarting;
Escape -> session running again; confirming it -> restart. Every path: one
dialog. No CRITICAL from cinnamon-session on cancel.

**compiz crashes at logout under option A - not our code, but our timing.**
compiz's XSMP die handler (`src/session.cpp`, `dieCallback`) calls `exit(0)`
from inside an ICE callback while other threads run. If GDBus's worker is
writing to the bus at that moment, it crashes in
`continue_writing_in_idle_cb` (backtrace:
[`compiz-exit-race-backtrace.txt`](compiz-exit-race-backtrace.txt); apport's
own cores were truncated by the reboot, so the kernel wrote this one to
`/var/tmp`). Under option A the session manager sends "die" milliseconds after
Unity answers `Open`, so the bus is busy: **3 crashes in 7 restarts**, against
none in about ten through the old two-dialog path. The user sees "Извините,
возникла внутренняя ошибка" at the next login. Nothing on Launchpad for this
function in compiz. Option A cannot ship until this is fixed.

**Experiment: `_exit(0)` in `dieCallback`**
([`compiz-die-exit.diff`](compiz-die-exit.diff), compiz `+exp1`): after
`CompSession::close()` leave without running exit handlers - the session is
over. Same target, same packages otherwise, the kernel writing any core to
`/var/tmp` before each restart: **0 crashes in 8 restarts** (boots 03:06 to
03:26), against 3 in 7 without it. At the old rate, eight clean restarts in a
row would happen about 1% of the time.

Also seen at every restart, old path and new: unity-settings-daemon (archive)
crashes in its color plugin during teardown (`libcolor.so`, signal handler).
Not investigated.

# Published: the #6 trio, verified from a clean snapshot

2026-09-24, with May's approval: unity `+unity4`, cinnamon-session
`6.4.2-1+unity1` and compiz `1:0.9.14.2+25.10.20250930-0ubuntu3+unity1`
(`_exit` in the XSMP die handler) are in our aptly. They go together:
cinnamon-session without the compiz fix brings the exit crashes back.

Verified by the delivery path: `target-desktop` rolled back to
`Clean-updated-2026-09-23` (boot 09:36:31, marker gone), our apt source added,
`apt-get install unity cinnamon-session compiz` - 13 packages upgraded,
dependencies resolved to our versions - rebooted
([`option-runs/trio-aptly/`](option-runs/trio-aptly/)):

- power key: Unity's dialog; menu -> restart with an inhibitor: Unity's
  inhibitor warning; Escape: session running; confirming: restart.
- five restarts through the new path (one confirmed past an inhibitor, four
  plain), cores written by the kernel: **no compiz crash**. No
  unity-settings-daemon crash either, which had crashed at almost every
  restart before the compiz fix - possibly a consequence of compiz's crash;
  observed, not investigated.

compiz `+unity1` needed three builds: `CompTimerTestCallback.TimerOrder`
failed twice - once while agent B was building, once with the builder
idle. The test checks callback order against real 500-1100 ms windows; it
does not touch `src/session.cpp`. A flaky test, not our change.

# Logout with an inhibitor hung the session; a hung session was then bypassed

2026-09-24, target, after the trio. Runs: [`option-runs/logout/`](option-runs/logout/),
[`refuse-before/`](option-runs/refuse-before/), [`logout-fixed/`](option-runs/logout-fixed/).

**The hang (cinnamon-session, old).** Unity's logout dialog calls
`Logout(1)` - no confirmation - after its own dialog. With an inhibitor,
cinnamon-session enters the query phase and sends the inhibitors to *the*
end-session dialog. There is none: no Cinnamon, no Gtk dialog, and option A
only engaged through `show_end_session_dialog`. Nothing on screen, no logout,
`IsSessionRunning` false for good. Same mechanism as rejected option B.

**The bypass (Unity, old).** In that state every Logout/Reboot/Shutdown call
gets `org.gnome.SessionManager.NotInRunning`, and Unity's error path fell back
to logind: `refuse-before` shows menu -> restart on a hung session restarting
the machine through `login1.Reboot`, past the inhibitor.

**Fixes, published 2026-09-24:**

- cinnamon-session `6.4.2-1+unity2`: when inhibitors have no dialog to go to,
  ask the shell for one (Gtk as the fallback).
- unity `+unity5`: fall back to logind only when the session manager is
  missing or broken, not when it answers `NotInRunning` or `LockedDown` -
  which would also have gone past a lockdown policy, under any session
  manager.

**Measured:** `+unity5` alone on the hung session - menu -> restart does
nothing (no logind call, same boot; Unity logs the refusal). With
cinnamon-session `+unity2` - logout with an inhibitor shows Unity's "у вас
открыты файлы ... перед завершением сеанса"; Escape leaves the session
running; confirming logs out (greeter up). The restart path still shows its
inhibitor warning. No unit test for the refusal: Unity's test D-Bus server
cannot return an error with a chosen name; the fallback tests (missing
handler) still pass, 51/51.
