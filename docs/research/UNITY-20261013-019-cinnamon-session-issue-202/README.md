# UNITY-20261013-019: linuxmint/cinnamon-session#202 against our cinnamon-session 6.4.2

Read-only check, 2026-10-13, agent B. Nothing was reproduced. The only commands on the target were passive
`systemctl` queries on target2.

## The report

[linuxmint/cinnamon-session#202](https://github.com/linuxmint/cinnamon-session/issues/202) (open, opened
2026-05-10): Linux Mint 22.2, cinnamon-session 6.4.0. When Obsidian (Electron) crashes with an `int3` trap, the
user session ends and LightDM shows the greeter. The report blames
`GLib-CRITICAL: g_variant_unref: assertion 'value != NULL' failed` in cinnamon-session.

A comment from 2026-06-10 reports the same with gnome-session on Ubuntu 24.04: `org.gnome.Shell@x11.service: Main
process exited, code=killed, status=9/KILL`, then the session ends.

## The g_variant_unref(NULL): fixed in our package and upstream

The critical comes from `close_end_session_dialog()` in `cinnamon-session/csm-manager.c`, next to
"Unable to close Cinnamon's end session dialog". 6.4.2 called `CloseEndSessionDialog` on org.Cinnamon and unreffed
the result without checking it.

- **Ours:** `debian/patches/Don-t-ask-a-Cinnamon-that-is-not-running-to-close-its-dia.patch`, in the package since
  6.4.2-1+unity1 (2026-09-23, `a8febcc`), so in every version we published. It skips the call when org.Cinnamon
  has no owner and unrefs only a result that exists.
- **Upstream:** master `cbcc364` "csm-manager.c: Clean up some end-session warnings" (2026-06-18, first in
  6.7.3) does the same: an owner check, and `g_variant_unref` only when the call has no error.

Without `G_DEBUG=fatal-criticals` this is a critical in the log, not an abort.

## What ends the session in #202

In the report's journal the session ends earlier, with
`CRITICAL: Unable to start session: Lost name on bus: org.gnome.SessionManager`. That is `main.c:82` →
`csm_util_init_error (TRUE, …)`, a deliberate exit when cinnamon-session loses its session-bus connection. The
`g_variant_unref` and `g_object_unref` criticals follow during the teardown. The same code is in 6.4.2 and in
master: without its bus the session manager cannot continue.

Why the bus goes away is not in the report's data, so **#202's own mechanism is UNKNOWN**.

Upstream master has two changes for one way the session bus can be stopped:
- `2605e63` "systemd: Exclude dbus.service from oomd coverage";
- `c038bb4` "systemd: Keep dbus.service running when the kernel OOM-kills one of its processes", which sets
  `OOMPolicy=continue`.

D-Bus-activated applications without a `SystemdService=` run in `dbus.service`'s cgroup, so with the default
`OOMPolicy=stop` a kernel OOM kill of one of them stops `dbus.service` and the session with it. That is plausible
for #202, and the `status=9/KILL` in the comment fits an OOM kill, but neither journal in the report shows an OOM
or oomd line.

On target2 (Ubuntu Unity 26.04, passive):
- systemd-oomd is not installed;
- the user `dbus.service` runs in `session.slice/dbus.service` with `OOMPolicy=stop` and
  `ManagedOOMPreference=none`.

Our 6.4.2 ships no systemd user drop-ins at all; master's came with its graphical-session.target support.
Carrying the `dbus.service` drop-in is UNITY-20261013-022.

## Result

ALREADY_FIXED for the defect the report names (`g_variant_unref(NULL)` at session end): patch already in our
package (`FIXED_LOCAL`), and fixed upstream in `cbcc364`. The session loss itself depends on why the session bus
stops. That is UNKNOWN for #202 and is followed up in UNITY-20261013-022.
