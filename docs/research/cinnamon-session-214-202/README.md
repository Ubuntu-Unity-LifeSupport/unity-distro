# cinnamon-session: linuxmint/cinnamon-session#214 and #202

Found by the stack-health survey (`../../STACK-HEALTH.md`).

## #214 - session not closed while a delay inhibitor holds a restart

Upstream: [#214](https://github.com/linuxmint/cinnamon-session/issues/214),
fixed by [9409c18b](https://github.com/linuxmint/cinnamon-session/commit/9409c18b05af6abbb8f0ac67314680211e8fd513)
(PR #215, 2026-09-21, 6.7 unstable only). On shutdown/restart
cinnamon-session asked logind and never quit; with a long `delay` inhibitor
the session stayed on screen half torn down.

**Under Unity it did not show, for the wrong reason.** Measured on target
with `+unity2`, `InhibitDelayMaxSec=60` and a root delay inhibitor, restart
from Unity's menu (`runs/cs-delay.sh`, `runs/01-unity2-delay-reboot.txt`):
"Requesting system restart" **12 times in 120 ms**. `end_phase()` runs again
for every client that exits during the EXIT phase and each run reached
`csm_manager_quit()`; logind accepted the first Reboot and refused the rest
with `OperationInProgress`, cinnamon-session took that as a failed restart,
fell back to "an MDM logout action" (MDM is long gone) and quit. The session
went away within 5 s by accident; the restart came at +60 s.

Fixed in cinnamon-session `6.4.2-1+unity3` (in aptly):
- the upstream commit, backported whole (it also drops MDM support): a
  delay inhibitor of its own, quit on logind's `PrepareForShutdown`;
- ours, `Request-the-reboot-or-shutdown-only-once.patch`: `csm_manager_quit()`
  acts once. Without it the backport would still quit on the repeats'
  refusal, logging a false "Shutdown/restart was not confirmed by logind".

Measured with `+unity3`, same test (`runs/02-unity3-delay-reboot.txt`): one
restart request, no refusal, session gone within 3 s, greeter at 4 s, the
machine restarted at +60 s as the inhibitor asked. A normal logout cycle
afterwards: clean.

Not changed: during the delay the greeter accepts a new login; lightdm does
not look at `PreparingForShutdown` (upstream remark in #214). Not ours to
fix in cinnamon-session.

## #202 - session ends when an Electron client crashes

Upstream [#202](https://github.com/linuxmint/cinnamon-session/issues/202),
open; the same report exists for gnome-session. The journal in it shows
`on_name_lost` with a NULL connection - cinnamon-session's **own** bus
connection closed ("Lost name on bus: org.gnome.SessionManager"), after
which ending the session is the only thing it can do. Nothing a crashing
client can cause from inside cinnamon-session; the cause is the bus
connection, not investigated (no reproducer).

The `g_variant_unref: assertion 'value != NULL' failed` in that report comes
from `close_end_session_dialog()` unref'ing the reply of a failed call; our
`+unity1` patch ("Don't ask a Cinnamon that is not running to close its
dialog") already checks it. Nothing else to change.

## #202 re-checked (A-4, 2026-09-26, agent A) - not reachable in our session

Upstream: issue open since 2026-05-10, no maintainer reply, no PR. Reporter:
Mint 22.2, Obsidian (Electron) hits a Chromium `int3` trap, and in the same
second cinnamon-session logs "Unable to start session: Lost name on bus:
org.gnome.SessionManager", the `g_variant_unref` warning, "Unable to close
Cinnamon's end session dialog: The connection is closed" - back to the greeter.
The only comment (GNOME 46) shows a different pattern. No gnome-session report
exists.

**Why a client cannot cause it** (code, 6.4.2 = master here): cinnamon-session
owns `org.gnome.SessionManager` with `G_BUS_NAME_OWNER_FLAGS_NONE`
(`cinnamon-session/main.c:150-156`) - no client can take the name over.
`on_name_lost` with a NULL connection (`main.c:77-96`) means cinnamon-session's
**own session-bus connection closed**; the "Unable to start session" prefix is
misleading. The `g_variant_unref(NULL)` is `close_end_session_dialog()`
unref'ing a failed call's reply - a GLib warning after the session is already
ending, not a cause; fixed upstream only in 6.7 (cbcc364), and in ours by the
`+unity1` patch "Don't ask a Cinnamon that is not running to close its dialog".

**Measured on target** (clean snapshot + our aptly, cinnamon-session
`6.4.2-1+unity3`, real input where input matters):
- journals of every boot on this disk: `g_variant_unref` appears **only in
  stock boots** (2026-09-23 and four boots on 2026-09-26 before the upgrade),
  always at shutdown from `close_end_session_dialog`; **0 in our boots**.
  "Lost name on bus" appears when the machine is rebooted with
  `systemctl reboot` - systemd stops the user bus under the session, harmless.
- clients crashing (`runs/crash-clients.sh`): nemo, gnome-text-editor,
  gnome-characters killed with SIGTRAP (the reporter's `int3`), SIGSEGV and
  SIGABRT, 9 kills - session untouched (same cinnamon-session and compiz),
  no lost name, no warning.
- logout through Unity's dialog x3, lock/unlock, switch user to a second
  account and back, that account logging out: no lost name, no warning, no
  CRITICAL from cinnamon-session.
- a menu restart was attempted but did not happen (the host appears to have
  slept mid-test: screen blanked, first ping 1 s); menu restarts on the same
  packages passed 4 of 4 earlier the same day (`../recheck-2026-09-26/`).

Nothing to change in cinnamon-session for #202. The trigger in the report
is the user bus going away; not investigated further without a reproducer.

**Found on the way, not #202 (low):** `Logout(1)` sent to a *background*
(switched-away) Unity session does not end it: a client misses the
query-phase reply, cinnamon-session wants a dialog, our `+unity1` path asks
that session's Unity (`org.gnome.Shell`), which does not answer from an
inactive VT ("Timeout was reached"), the GTK fallback reports "Session not in
running phase" and the session waits until the user switches back; then a
Logout ends it at once. Not a user-facing path in normal use (logout is
requested from the active session); recorded for later.
