# UNITY-20260928-022: unity-settings-daemon power - registrations that outlive stop()

Follow-up of UNITY-20260927-012. Its Design Challenger listed, by code
reading, other registrations of the power manager that `stop()` does not
undo: idle-monitor watches, the D-Bus object on the session connection,
timers, async proxy creation without a cancellable, notification weak
pointers. This task checks which of them actually fire after `stop()` and
with what effect, and fixes only the proven ones, on top of +unity7
(`b570a22`). Agent A, target `target-desktop`, 2026-09-29.

Two states matter: **stopped** - the plugin switched off
(`com.canonical.unity.settings-daemon.plugins.power active false`): `stop()`
ran, the manager lives on; **finalized** - after the session manager's
`Stop`, `gnome_settings_manager_stop()` unloads the plugins and the manager is
freed while the main loop finishes its iteration (UNITY-20260927-012's
mechanism). Tests on u-s-d +unity7 with its dbgsym; the finalized state is
forced under gdb as in 012 (`gnome_settings_manager_stop
(gnome_settings_manager_new ())`, loop left running, perturb drop-in).

## Results

| Registration | Fires after stop? | Effect | Evidence |
|---|---|---|---|
| D-Bus object `/org/gnome/SettingsDaemon/Power` (registered once in `on_bus_gotten`, never unregistered; the name is released only in `finalize`) | **yes** | stopped: `handle_method_call` returns without replying (`if (manager->priv->session == NULL) return;`) - `Screen.GetPercentage` took 0.12 s with the plugin running, **28 s (client timeout)** after it was switched off; finalized: **SIGSEGV in `handle_method_call`** on the freed manager (apport report) | `runs/01`, `runs/02` |
| async proxy creation in `start()` (UPower keyboard backlight, session Presence; NULL cancellable) | **yes** | switched on and off at once, 3 of 3: `power_keyboard_proxy_ready_cb` / `session_presence_proxy_ready_cb` ran after `STOP` and stored new proxies in the stopped manager (`upower_kdb_proxy`, `session_presence_proxy`) - leaked on the next `start()`, which creates them again; after a finalize the same write would be to freed memory (only if the process ends within milliseconds of a start) | `runs/03` |
| idle-monitor watches (dim, blank, sleep, sleep warning, user-active) on the process-wide core monitor | **no - never registered on our stack** | `idle_configure()` returns early when `is_session_active()` is false; it reads the session manager's `SessionIsActive`, which **cinnamon-session does not export** (it exports `SessionName`, `InhibitedActions`), so no watch is ever added: traced `idle_configure` -> `idle_set_mode 0`, no `gsd_idle_monitor_add_idle_watch`, with a 20 s AC sleep timeout set | `tools/idle-diag.sh` (output in the task log); `runs/01`: no idle callback in 30 s idle |
| timers with `manager` as data: critical-battery actions (:1509, :1540), `temporary_unidle_on_ac` (:2661) | not reachable here | need a battery / the idle modes above; the VM has neither | code |
| notification weak pointers (:987) | not reachable here | notifications come from battery events | code |
| logind `g-signal` (:3214) | not tested | per-manager proxy, lives only while an in-flight call holds it | code (Design Challenger) |

**Side finding (outside this task's fix):** because cinnamon-session does not
export `SessionIsActive`, the power plugin's idle handling - dim, blank and
sleep on inactivity - never runs in Ubuntu Unity 26.04 with cinnamon-session:
`sleep-inactive-ac-*` / `-battery-*` have no effect through u-s-d. Reported
to the coordinator as a separate question (does anything else do it?).

Upstream: gnome-settings-daemon master has the same two defects (the silent
`return` when stopped and no `unregister_object`; checked in its
`gsd-power-manager.c`).

## Evidence card

```yaml
task_id: UNITY-20260928-022
package: unity-settings-daemon
target_series: resolute
issue: power plugin registrations outliving stop() - which fire, with what effect
status: REPRODUCED   # D-Bus object (stopped: calls hang; finalized: SIGSEGV), async start callbacks after stop (leak); idle watches and battery paths unreachable on our stack
issue_search_result: NOT_FOUND   # follow-up of UNITY-20260927-012; upstream master has the same code
source_version: 15.04.1+21.10.20220802-0ubuntu7+unity7 (built, not published; waits for the aptly freeze)
binary_version: same, on target for the tests
source_commit: Ubuntu-Unity-LifeSupport/unity-settings-daemon a/UNITY-20260927-012 b570a22
reproduction: tools/power-after-stop.sh stopped|finalized; the quick on/off toggle (runs/03)
reproduction_result: PASS
root_cause: >-
  (1) the D-Bus object is registered for the life of the process and its
  handler neither replies when the manager is stopped nor is removed when the
  manager is finalized; (2) the async proxy creations in start() cannot be
  cancelled and their callbacks write into the manager unconditionally
invariant: >-
  no D-Bus call to the power object is left without a reply, and none reaches
  a finalized manager; no start()-time async callback changes a manager that
  has stopped
existing_fix_result: NOT_FIXED
candidate_approaches:
  - "D1: stopped -> reply with a D-Bus error (method calls; get_property sets
    an error); finalize -> unregister the object registrations (ids kept from
    on_bus_gotten) before the manager is freed"
  - "D2: register the object in start() and unregister it in stop() (and own
    the name there): the object's life follows the running state; larger
    change, start() then needs the bus connection that is obtained
    asynchronously in new()"
  - "A1: a per-start GCancellable, cancelled in stop(); the two ready
    callbacks finish into a local and return without touching the manager
    when cancelled"
chosen_approach: D1 + A1 (to be reviewed)
correct_layer: >-
  The power manager owns its D-Bus registration and its async calls; its
  lifetime functions (stop, finalize) must end them. D1 keeps the
  registration lifetime = the manager object's lifetime and makes the
  stopped state answer; A1 is the pattern bus_cancellable already uses
  for g_bus_get in the same file.
unknowns:
  - "Natural reachability of the finalized D-Bus crash: a Power call already
    queued in the main-loop iteration of Stop (e.g. a brightness key at
    logout) - not observed."
  - "Whether the power plugin being switched off happens in practice (a
    dconf setting; the hang is then user-visible through media-keys'
    brightness calls - not measured)."
  - "The side finding (idle handling dead under cinnamon-session)."
design_challenger_required: true
architectural_task: false
design_review_result: PENDING
```
