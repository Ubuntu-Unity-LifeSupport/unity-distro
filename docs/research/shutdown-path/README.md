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
   `/org/Cinnamon`. Under Unity there is no Cinnamon shell, the call fails with
   `NAME_HAS_NO_OWNER`, and it falls back to its own GTK dialog -
   `cinnamon-session-quit`, the second dialog.
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
