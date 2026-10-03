# UNITY-20261002-003: the power plugin's idle watches outlive stop()

From UNITY-20260928-022 (side finding and dependency). Bundled with
UNITY-20260927-053 by C's decision (2026-10-03): cinnamon-session will
export `SessionIsActive` (F2), which makes the power plugin's idle handling
reachable; this task closes the gap that handling has, and ships first as
u-s-d +unity11. Agent A, target `target-desktop`.

## Mechanism (code, FACT)

`plugins/power/gsd-power-manager.c` (+unity10):

- `idle_configure()` adds up to four watches on the process-wide core idle
  monitor (`gsd_idle_monitor_get_core()`): `idle_dim_id`, `idle_blank_id`,
  `idle_sleep_warning_id`, `idle_sleep_id` (lines 2543-2623), each with
  `manager` as callback data (`idle_triggered_idle_cb`, line 2927ff), and
  `idle_set_mode()` adds a user-active watch (line 2354).
- `idle_configure()` removes them itself only when the session is inactive
  or idle is inhibited (lines 2509-2521, `clear_idle_watch`).
- `gsd_power_manager_stop()` only drops its reference to the monitor
  (`g_clear_object (&manager->priv->idle_monitor)`) and leaves the watches
  registered: after a stop they fire into a stopped manager (and after
  finalize into freed memory), and a later `start()` adds a second set.
- Today under cinnamon-session none of this is reachable: `is_session_active()`
  reads `SessionIsActive`, absent -> FALSE -> `idle_configure` takes the
  clear path every time (UNITY-20260928-022 measured no watch ever added).
  With F2 the watches are added on every session start.

## Reproduction "before" (2026-10-03, +unity10, `runs/01-before-unity10.txt`)

`tools/idle-after-stop.sh` (gdb as root on the running u-s-d, dbgsym): at the
first `idle_configure` after a plugin restart it sets `is_virtual_machine = 0`
and forces `SessionIsActive = TRUE` in the session proxy's cache (DC G5);
`sleep-inactive-ac-timeout` 15 s / `blank` for the run (the VM has no
backlight and no screensaver, so only the sleep watch is added). Note
(Verifier, 2026-10-03): the `is_virtual_machine = 0` set at the first
`idle_configure` inside `start()` is overwritten by `start()` itself
(`gsd-power-manager.c:3441`), so `idle_set_mode` stayed a no-op in runs 01
and 02: they test the watch registration (the sleep watch firing after
stop), not the idle modes, the user-active watch or the temporary-unidle
timer; run 03 repeats "after" with `gnome.is_vm=0`. Result:
the sleep watch fires once while the plugin runs (`IDLE-CB watch=4`); at
`stop()` the watch is still registered (`sleep=4`) and `stop()` leaves it;
after an input that resets the idle time the same watch fires again 15 s
later, into the stopped manager: **1 idle callback after stop**. No crash
on this run (`idle_set_mode` then calls `is_session_active` on the NULL
session proxy, a GLib critical path). Harness note: a gdb ended with
SIGTERM left its breakpoint behind once and u-s-d died of SIGTRAP
(NRestarts 1, crash file removed); the tool now ends gdb with SIGINT.

## Plan

1. Reproduce "before": with the property forced (gdb `return 1` in
   `is_session_active`, or the F2 prototype session manager), short idle
   timeouts, plugin switched off (`active=false`): the idle callbacks still
   fire (dim/blank) -> a callback into a stopped manager; trace with gdb
   dprintf / bpftrace as in -022.
2. Fix: `stop()` removes the idle watches and the user-active watch and
   resets the idle mode to NORMAL before dropping the monitor (the same
   sequence `idle_configure` uses on an inactive session); `finalize` is
   covered by `stop()` being called from it.
3. "After": the same run, no callback after stop; keyboard/power regressions
   of -022 and -002; Verifier; publication through the slot as u-s-d
   +unity11, before cinnamon-session F2.

## Implementation (2026-10-03)

u-s-d `15.04.1+21.10.20220802-0ubuntu7+unity11`, branch `a/UNITY-20261002-003`
of Ubuntu-Unity-LifeSupport/unity-settings-daemon (`89648a3`, fix
`cc675a5` on +unity10 `122c413`):
- `idle_watches_remove ()`: `clear_idle_watch` for the dim, blank,
  sleep-warning, sleep and user-active watches (on `priv->idle_monitor`, or
  the core monitor once that is NULL - G4b), `g_source_remove` of
  `temporary_unidle_on_ac_id`, `notify_close_if_showing` of the sleep
  warning, `current_idle_mode`/`previous_idle_mode` and
  `screensaver_active` reset directly (not through `idle_set_mode`, which
  returns early when inactive or on a VM);
- called from `stop()` before `g_clear_object (&idle_monitor)` and from
  `finalize` (which does not call `stop()` - D5);
- `priv->idle_user_active_id`: the user-active watch keeps its id, is
  added only when none is registered (G4a), and the id is cleared in
  `idle_became_active_cb` (the monitor removes a fired user-active watch);
- `debian/unity-settings-daemon-schemas.gsettings-override`:
  `sleep-inactive-ac-timeout=0` for the Unity power schema (G6; installed
  by `dh_installgsettings`, compat 13).
Gated build on the pinned chroot: `build/`.

## Reproduction "after" (2026-10-03, +unity11, `runs/02-after-unity11.txt`)

The same tool on the gated +unity11 debs (dpkg, with dbgsym): the sleep
watch fires once while the plugin runs (`IDLE-CB watch=4`), is registered
at `stop()` (`sleep=4`), and after the stop and the idle reset **no idle
callback runs: 0 after stop** (before: 1). u-s-d NRestarts 0, no crash
file. With +unity11 installed the override is effective in the session:
`sleep-inactive-ac-timeout=0`, battery `1200`, `idle-dim=true`;
`/usr/share/glib-2.0/schemas/10_unity-settings-daemon-schemas.gschema.override`
shipped by the schemas deb.

## Run 03: "after" with the idle path live (2026-10-03, `runs/03-after-unity11-is_vm0.txt`)

After the Verifier's remark: `gnome.is_vm=0` on the kernel command line
(changed test condition, GRUB set 2026-10-02T23:26:03Z, booted 23:29:58Z,
`/proc/cmdline` checked), cinnamon-session +unity4 (F2) installed so
`SessionIsActive` is real. The session was on the light-locker greeter after
a suspend (light-locker locks on suspend), so the harness still forced the
property in the cache for this run. Result: `idle_set_mode` acts now
(`SET-MODE 3`, `SET-MODE 2`, ...), one user-active watch (`user_active=15`)
across all transitions (G4a), and at `stop()` blank=16, sleep=17 and the
user-active watch are registered with `mode=3`; **after the stop and two
idle resets: 0 callbacks.** The full path - idle watches, user-active watch,
mode reset - is now shown at runtime, not only by review.

Harness incident (`runs/03a-INVALID-suspended-by-harness.txt`): a first
attempt set the 15 s AC timeout before the `blank` type; with the idle path
live the sleep watch fired in between with the default type `suspend` and
the guest suspended (02:32:06, woken 02:39). Configured behaviour, not a
defect; the tool now sets the type first.

## UNITY-20261002-011: the AC sleep override (decision 2026-10-02)

May's decision (via C): on mains power the machine does not suspend on
idle, as Ubuntu does for `org.gnome`; idle dimming stays; battery defaults
untouched. Task UNITY-20261002-011 was opened for unity-session; **moved to
unity-settings-daemon** (C, 2026-10-02, on the Design Challenger round 2
recommendation G6): `debian/unity-settings-daemon-schemas.gsettings-override`
in +unity11 - the schema's own package, `dh_installgsettings` priority 10,
no conflicting key with `10_ubuntu-settings` (correction after the Verifier:
that file *does* have a `[com.canonical.unity.settings-daemon.plugins.power]`
section - button-power, button-sleep, critical-battery-action - but no
`sleep-inactive-ac-timeout`; the effective values are as intended), and it ships in the
same publication as -003, before cinnamon-session F2, so there is no window
in which the idle policy runs without it. -011 closes through
`published_by` UNITY-20261002-003, with its own gated build of the same
commit (byte-identical, as UNITY-20260927-052).

Verification after F2 (C's condition): >= 25 min idle on AC, no suspend,
dim happens. On `target-desktop` this needs `gnome.is_vm=0` on the kernel
command line, because u-s-d does no idle transition on a VM and "did not
suspend" would prove nothing.

**Changed test condition (C, 2026-10-03): VM detection switched off so that
the idle path is reachable.** Not a u-s-d test drop-in but a workaround for
the test bench; the GRUB line is restored after the check and verified from
inside the guest (`/proc/cmdline`). Install and removal times are recorded
in the run file. The parameter works in +unity11 (`89648a3`), shown in code:

- `plugins/power/gpm-common.c:986` `parse_vm_kernel_cmdline ()` reads
  `/proc/cmdline` (`:995`), matches `gnome.is_vm=(\S+)` (`:998`) and sets
  `*is_virtual_machine = atoi (arg)` for `0`/`1` (`:1008`);
- `gpm-common.c:1025` `gsd_power_is_hardware_a_vm ()` calls it first
  (`:1034` `if (parse_vm_kernel_cmdline (&ret)) return ret;`), *before*
  the systemd `Manager.Virtualization` property (`:1052`);
- `gsd-power-manager.c:3441` `priv->is_virtual_machine =
  gsd_power_is_hardware_a_vm ();` in `start()`.
So `gnome.is_vm=0` gives `is_virtual_machine = FALSE` without gdb; the gdb
route of G5 is not needed for this check.

Report items (C): the effective `sleep-inactive-ac-timeout` (`gsettings get`
from the session), >= 25 min idle without a transition to sleep, the DIM
transition in the trace (no backlight on the VM, so dim shows as the idle
mode change, not on screen).

## Target test of the override: 27 min idle on AC (2026-10-03, `runs/04-ac-idle-27min*.txt`)

C's condition for this publication (the override ships in it). Conditions:
`gnome.is_vm=0` (changed test condition, see above), F2 installed so
`SessionIsActive` is real, and light-locker's lock after the screensaver
switched off for the run (`apps.light-locker lock-after-screensaver` 5 -> 0
-> restored 5): with the lock the session goes inactive at about 5 min and
u-s-d drops every idle watch, so "no suspend" would not be the override's
doing.

- **Effective value from the session:** `sleep-inactive-ac-timeout=0`
  (type `suspend`, `idle-dim=true`, session `idle-delay=300`).
- **27 minutes without a transition to sleep:** 23:47:22Z - 00:14:34Z, the
  session on VT 7 and `SessionIsActive=true` every minute; no logind suspend
  message in the window (0 matches); uptime continuous. The gdb trace
  (breakpoints on `idle_set_mode` and `idle_triggered_idle_cb` set at lines
  2318 and 2956) shows no idle callback and no mode change: no sleep watch
  was registered, which is what `sleep-inactive-ac-timeout=0` does.
- **Control** that this measurement sees a suspend: run 03a - the same
  path with a 15 s AC timeout and type `suspend` suspended the guest
  within a second.
- **DIM:** not on AC by design - `idle_configure` skips the dim watch when
  `!on_battery` ("Don't dim when charging", as upstream); the VM has no
  battery. `idle-dim=true` is untouched by the override. Not testable here.
- **Blank on screensaver:** not reached in this run (the power plugin's
  `screensaver_active` stayed FALSE); not part of this publication.

## Regressions on +unity11 (2026-10-03, `runs/05-regressions-unity11.txt`)

On target with +unity11 (and F2, `gnome.is_vm=0`): UNITY-20260928-022
`power-dbus-checks.sh` ("not running" answers while stopped, inhibitors back)
and `keyboard-toggle-race.sh` (every call answered, same pid, 0 crash);
UNITY-20260927-012 `usd-power-regress.sh` (session callbacks 2/0/2 -> 4 after
on) and `usd-color-uaf.sh` (STOP-CALLED, alive, 0 journal lines);
UNITY-20260927-052 `two-clients.sh` (SURVIVED); UNITY-20261002-002
`stop-before-bus.sh stop` (name owned after start and after off/on,
`bus_cancellable` unchanged). NRestarts 0, 0 crash files.

## Target test in the users' environment (2026-10-03, `runs/06-users-environment-boot.txt`)

C's condition for the gate: what users will get - the published
cinnamon-session 6.4.2-1+unity3 (the F2 change of UNITY-20260927-053 is not
part of this publication and was removed from target), GRUB without
`gnome.is_vm=0` (restored 2026-10-03T00:23:45Z, `/proc/cmdline` checked),
u-s-d +unity11 from the gated build. One natural boot: the Power name is
owned, NRestarts 0, no replaced mapping, 0 crash files, `dpkg -V` clean
for u-s-d and cinnamon-session, `sleep-inactive-ac-timeout=0` effective;
`SessionIsActive` absent (as expected without F2: the idle path stays
unreachable for users until F2 ships, and the override is already in
place for that day).

The runs 03-05 used a changed environment (F2 installed, `gnome.is_vm=0`)
to make the idle path reachable; they are recorded as such.

## Evidence card

```yaml
task_id: UNITY-20261002-003
package: unity-settings-daemon
target_series: resolute
issue: power plugin idle watches on the shared idle monitor are not removed in stop()
status: INVESTIGATING
issue_search_result: PENDING
existing_fix_result: PENDING
source_version: 15.04.1+21.10.20220802-0ubuntu7+unity10 (published)
root_cause: stop() clears the idle_monitor reference without removing the watches it registered
root_cause_mechanism: watches hold `manager` as data on the process-wide core monitor; they survive stop() and finalize; start() adds a second set
invariant: the power manager's idle watches do not outlive stop()
chosen_approach: PENDING (Design Challenger before code, with UNITY-20260927-053 F2)
related: UNITY-20260927-053 (F2 makes the path reachable), UNITY-20260927-012 (same pattern for the session/screensaver handlers, fixed in +unity7)
```
