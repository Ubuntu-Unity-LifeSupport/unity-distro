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
