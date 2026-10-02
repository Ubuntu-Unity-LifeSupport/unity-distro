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
| D-Bus property Get (`handle_get_property` returns NULL without setting an error) | **yes - aborts the daemon** | GDBus asserts `error != NULL` (`invoke_get_property_in_idle_cb`, gdbusconnection.c:4771) and u-s-d dies with SIGABRT, systemd restarts it: `Properties.Get ... Percentage` with the plugin stopped, **and with it running on a machine without a battery** (percentage < 0 -> NULL). Our own clients do not trigger it: u-c-c's power and screen panels load properties with GetAll (NULL is skipped there) - opened both, u-s-d survived | `runs/04` |
| async calls made by `start()`: proxy creation (UPower keyboard backlight, session Presence) and logind `Inhibit` (`inhibit_suspend`, `inhibit_lid_switch`), all with a NULL cancellable | **yes** | switched on and off at once, 3 of 3 (`runs/03`, `runs/04`): the ready callbacks ran after `STOP` and wrote into the stopped manager - the session Presence proxy (leaked only through this race) and the inhibitor fds; no leaked logind inhibitor was seen in the final state. Separately, `upower_kdb_proxy` is never cleared in `stop()` or `finalize` and leaks on every restart of the plugin, race or not (code). After a finalize these writes would be to freed memory (only if the process ends within milliseconds of a start) | `runs/03`, `runs/04` |
| idle-monitor watches (dim, blank, sleep, sleep warning, user-active) on the process-wide core monitor | **no - never registered on our stack** | `idle_configure()` returns early when `is_session_active()` is false; it reads the session manager's `SessionIsActive`, which **cinnamon-session does not export** (it exports `SessionName`, `InhibitedActions`), so no watch is ever added: traced `idle_configure` -> `idle_set_mode 0`, no `gsd_idle_monitor_add_idle_watch`, with a 20 s AC sleep timeout set | `tools/idle-diag.sh` (output in the task log); `runs/01`: no idle callback in 30 s idle |
| timers with `manager` as data: critical-battery actions (:1509, :1540), `temporary_unidle_on_ac` (:2661) | not reachable here | need a battery / the idle modes above; the VM has neither | code |
| notification weak pointers (:987) | not reachable here | notifications come from battery events | code |
| logind `g-signal` (:3214) | not tested | per-manager proxy, lives only while an in-flight call holds it | code (Design Challenger) |

Why removing the object in `finalize` is enough for calls already queued
(INFERENCE from GLib's gdbusconnection.c, stated by the Design Challenger): a
call to a registered object is dispatched from an idle callback that looks
the registration up again and answers with an error when it is gone, for
methods and for property Get alike; `finalize` runs on the same main context,
so nothing is dispatched while it runs.

Known gap, not fixed here: `stop()` cancels and frees `bus_cancellable` and
`introspection_data`; if it runs before `on_bus_gotten`, the object is never
registered and the name never owned, and nothing in `start()` redoes it -
Power stays absent until the daemon restarts (code, Design Challenger).

**Side finding (outside this task's fix):** because cinnamon-session does not
export `SessionIsActive`, the power plugin's idle handling - dim, blank and
sleep on inactivity - never runs in Ubuntu Unity 26.04 with cinnamon-session:
`sleep-inactive-ac-*` / `-battery-*` have no effect through u-s-d. Reported
to the coordinator as a separate question (does anything else do it?).
**Dependency:** whatever makes that idle handling work (a session manager
exporting `SessionIsActive`, or a shim) makes the idle watches reachable
after `stop()` at once - `stop()` only drops its reference to the
process-wide core monitor and leaves the watches with the manager as data -
so that change must remove the idle watches in `stop()` in the same step.

Upstream (gnome-settings-daemon master's `gsd-power-manager.c`): its method
handler has the same silent `return` when stopped and there is no
`unregister_object`; its property handler already sets an error when stopped
("No session"); it passes a per-manager cancellable to its proxy creations.
Upstream is a GApplication, so its finalized case is structured differently.

## Fix: u-s-d +unity8, measured

`15.04.1+21.10.20220802-0ubuntu7+unity8` = +unity7 (`b570a22`) + the fix
(`27e75f4`) + changelog (`41fd7eb`), branch `a/UNITY-20260928-022` on
Ubuntu-Unity-LifeSupport/unity-settings-daemon; built with
`scripts/build_sbuild.py`, exit 0 (`build/…build-manifest.json`). On target
with its dbgsym and the perturb drop-in; +unity7 for comparison (`runs/05`):

| Check | +unity7 | +unity8 |
|---|---|---|
| `Properties.Get Percentage`, plugin running, no battery | u-s-d **aborts** (NoReply after 7.7 s, restarted) | error "Property Percentage is not available" in 0.1 s, daemon alive (`runs/06`) |
| Get / `Screen.GetPercentage`, plugin stopped | abort / 28 s timeout (`runs/01`, `runs/04`) | "The power plugin is not running" in 0.04 s, daemon alive (`runs/06`) |
| quick on/off x3 then on: u-s-d's logind inhibitors | - (daemon had restarted) | while stopped only media-keys' key-handling block; after re-enabling the lid-switch block **and the `sleep` delay inhibitor are back** (`runs/06`) |
| forced finalize, then `Screen.GetPercentage` by the well-known name | SIGSEGV in `handle_method_call` (`runs/02`) | ServiceUnknown, no crash (`runs/07`) |
| forced finalize, then method and property Get **by u-s-d's unique name** (reaching the connection) | - | "object /org/gnome/SettingsDaemon/Power does not exist" for both, no crash (`runs/08`) |

## Verifier round 1 (+unity8): FAIL - keyboard calls before the proxy is back

The independent Verifier confirmed every row above and found a new crash
(`runs/09-verifier-1-unity8.txt`, `tools/kbdrace.py`,
`tools/keyboard-toggle-race.sh`, both written by the Verifier): with 20
`Keyboard.StepUp` calls kept in flight while the plugin was switched off and
on 15 times, u-s-d died with SIGSEGV, 2 of 2 (`libpower.so+0x90a8`,
`upower_kbd_get_brightness`, gsd-power-manager.c:1920, `error->domain` with
`error == NULL`; journal: `g_dbus_proxy_call_sync_internal: assertion
'G_IS_DBUS_PROXY (proxy)' failed`). +unity8's `stop()` clears
`upower_kdb_proxy`, and `start()` creates it again asynchronously: between
the two the plugin is running with a NULL proxy, and the Keyboard handler
called the helpers without checking it. In +unity7 the same path exists only
at the first start or when the proxy could not be created (code, not run).
The same race with `Screen.GetPercentage` (11,806 calls) answered every call.

Fix (`df68430`, changelog +unity9 `57945f5`): the Keyboard method handler
answers "No keyboard backlight" while there is no proxy; the helpers' other
callers already check it.

## Verifier round 2 (+unity9): PASS

`runs/11-verifier-2-unity9.txt`: round 1's keyboard race twice, and StepDown,
Toggle and every method and property mixed under 25 irregular toggles - the
"No keyboard backlight" window was hit hundreds of times per method, every
call answered (slowest 0.089 s), no Timeout/NoReply; `power-dbus-checks.sh`,
quick toggles (inhibitors back each time), forced finalize by unique name -
all pass; no crash, NRestarts 0. Code review: no defect against the
invariant; the fields used by the Screen/GetDevices/property handlers are set
synchronously in `start()` with `session`. Two pre-existing points noted, not
blocking: `on_bus_gotten` would not release an older connection/name id (it
runs once per manager), and `stop()` leaves the idle watches (never
registered on our stack - see the side finding above).

## Gated build for publication (2026-10-02)

- Build: `scripts/build_sbuild.py` from `packages/unity-settings-daemon` at
  `57945f5` (a fresh clone of Ubuntu-Unity-LifeSupport/unity-settings-daemon,
  ref `a/UNITY-20260928-022`), on the pinned chroot 20260929T201245Z
  (UNITY-20260929-016); manifest
  `build-gated/UNITY-20260928-022-unity-settings-daemon-build-manifest.json`.
- Against the tested build `build-unity9/`: all 5 debs and 2 ddebs
  byte-identical (`build/gated-vs-tested.txt`). The tested build has no
  chroot record, so `tested_build` is `this_build`, with the key runs
  repeated on target on the gated debs.
- The gated source package is format 1.0 native (one `.tar.gz`), the tested
  one orig + diff; the binaries are unaffected and our repository publishes
  binaries. Same as UNITY-20260927-012's gated build.
- `docs/PATCHES.md`: section for +unity9 appended in main `9807121`.
- Short Verifier on the gated build: PASS (REVIEWED).
- Order: u-s-d +unity7 (UNITY-20260927-012) is published and verified on
  target first; then +unity9 is installed there for the key runs.

## After publication: Power not registered at one session start (2026-10-02)

+unity9 was published (snapshot `unity-resolute-20260928-022`). The target
check, through the repository and **without** the test drop-in, found:

- First boot: u-s-d running, the power plugin active (its logind
  inhibitors taken), NRestarts 0, no crash - but
  `org.gnome.SettingsDaemon.Power` had **no owner**; u-s-d's other names
  were there. Every Power call answered ServiceUnknown.
- Second boot: the name was there. Three `systemctl --user restart`s: there
  each time. So 1 of 2 boots.

This is the **known gap** recorded above and in the evidence card's unknowns
("stop() before on_bus_gotten leaves Power unregistered until restart"):
`register_manager_dbus()` runs once per process (from
`gsd_power_manager_new`); `stop()` cancels `bus_cancellable` and frees
`introspection_data`; a stop before the bus result arrives makes
`on_bus_gotten` return on CANCELLED, and no later `start()` registers again.

It is **not new in +unity9**: the cancel in `stop()` is in `ubuntu/devel`
(the archive's 0ubuntu6, since the 2014 import), `unity/resolute` and +unity7
`b570a22`; 27e75f4 added a second cancel in `finalize` and left `stop()`'s
as it was. Measured on target with `tools/stop-before-bus.sh` (u-s-d under
gdb; after `gsd_power_manager_start()` returns, `gsd_power_manager_stop()` is
called before the main loop delivers the bus result; then the plugin is cycled
with gsettings `active` false -> true):

| Version | no stop | stop before the bus result |
|---|---|---|
| +unity9 (published) | name owned, Get Icon answered (`runs-race/01`) | no owner after start or after the off/on cycle, ServiceUnknown (`runs-race/02`) |
| +unity7 (published) | name owned, Get Icon answered (`runs-race/03`) | the same: no owner, ServiceUnknown (`runs-race/04`) |

No crash in any run; back under systemd the name is owned. Not known yet:
what stopped the power plugin during that session start. All runs before
publication had the perturb drop-in (`G_MESSAGES_DEBUG=all`, malloc
tunables) and did not show it; the one +unity7 boot without the drop-in
owned the name, which is too few to compare rates.

**Lesson.** The gap was found by the Design Challenger, written into this card
and listed as a follow-up candidate in the handoff of 2026-09-29, but no task
was opened on the board and it was not closed or re-checked before
publication. Its user-visible effect (no Power D-Bus for the session:
brightness keys, the power indicator's level) was not measured. A known gap
in the code path a task changes needs a board task, or a measurement of its
effect, before the gate; and the target check of a publication runs without
test drop-ins, as this one did.

## Evidence card

```yaml
task_id: UNITY-20260928-022
package: unity-settings-daemon
target_series: resolute
issue: power plugin registrations outliving stop() - which fire, with what effect
status: BLOCKED   # aptly freeze, resume REVIEW; fix verified (+unity9). Found: D-Bus object (stopped: calls hang; finalized: SIGSEGV), async start callbacks after stop (leak); idle watches and battery paths unreachable on our stack
issue_search_result: NOT_FOUND   # follow-up of UNITY-20260927-012; upstream master has the same code
source_version: 15.04.1+21.10.20220802-0ubuntu7+unity7 (base; built, not published; waits for the aptly freeze)
candidate_version: 15.04.1+21.10.20220802-0ubuntu7+unity9   # +unity8 superseded (Verifier round 1 FAIL), never published
candidate_commit: Ubuntu-Unity-LifeSupport/unity-settings-daemon a/UNITY-20260928-022 57945f5 (27e75f4 + df68430)
verifier_result: PASS   # round 2 on +unity9 (runs/11); round 1 FAIL on +unity8 (runs/09)
binary_version: same, on target for the tests
source_commit: Ubuntu-Unity-LifeSupport/unity-settings-daemon a/UNITY-20260927-012 b570a22
reproduction: tools/power-after-stop.sh stopped|finalized; the quick on/off toggle (runs/03)
reproduction_result: PASS
root_cause: >-
  (1) the D-Bus object is registered for the life of the process; its method
  handler does not reply when the manager is stopped, its property handler
  returns NULL without an error (stopped, or a property without a value),
  and it is not removed when the manager is finalized; (2) the async calls
  start() makes (two proxy creations, two logind Inhibit calls) cannot be
  cancelled and their callbacks write into the manager unconditionally
invariant: >-
  every D-Bus call to the power object gets a reply or an error, none aborts
  the daemon and none reaches a finalized manager; no async call made by
  start() (proxies, logind inhibitors) changes a manager after stop()
existing_fix_result: NOT_FIXED
candidate_approaches:
  - "D1: stopped -> reply with a D-Bus error (method calls; get_property sets
    an error); finalize -> unregister the object registrations (ids kept from
    on_bus_gotten) before the manager is freed"
  - "D2: register the object in start() and unregister it in stop() (and own
    the name there): the object's life follows the running state; larger
    change, start() then needs the bus connection that is obtained
    asynchronously in new()"
  - "A1: a per-start GCancellable (start_cancellable), cancelled in stop()
    and finalize, passed to the two proxy creations and the two logind
    Inhibit calls; each callback finishes into a local and returns before
    casting user_data when cancelled; the inhibitor-taken flags are reset in
    stop() (else a cancelled request would never be made again after a
    restart - the lock-before-suspend inhibitor would be lost); the keyboard
    backlight proxy is cleared in stop()"
chosen_approach: D1 (method error, property errors on every NULL path, unregister in finalize before the connection is cleared, bus_cancellable also cancelled in finalize) + A1; commit 27e75f4 on a/UNITY-20260928-022 (on +unity7 b570a22), changelog +unity8 41fd7eb (reworded after review 2; first version 6a12166/6465110, same code, never pushed or built to the end)
correct_layer: >-
  The power manager owns its D-Bus registration and its async calls; its
  lifetime functions (stop, finalize) must end them. D1 keeps the
  registration lifetime = the manager object's lifetime and makes the
  stopped state answer; unregistering in finalize is enough for calls already
  queued because GDBus looks the registration up again before dispatching
  (INFERENCE from GLib). A1 is the pattern bus_cancellable already uses for
  g_bus_get in the same file and upstream uses for its proxies. D2 (register
  in start, unregister in stop) was rejected: it moves the async bus fetch
  into start() and races it with toggling.
unknowns:
  - "Natural reachability of the finalized D-Bus crash: a Power call already
    queued in the main-loop iteration of Stop (e.g. a brightness key at
    logout) - not observed."
  - "Whether the power plugin being switched off happens in practice (a
    dconf setting; the hang is then user-visible through media-keys'
    brightness calls - not measured)."
  - "The side finding (idle handling dead under cinnamon-session) and its dependency on the idle watches."
  - "The logind g-signal handler (:3214) is not disconnected before its proxy is dropped; an in-flight call could keep the proxy alive - not tested. If a PrepareForSleep (resume) then reaches a stopped manager, handle_resume_actions calls inhibit_suspend, which sets inhibit_suspend_taken with no proxy; the next start() would skip the lock-before-suspend inhibitor until the next resume (Design Challenger, review 2, R1). Not fixed here: not reproduced; proposed as a one-line follow-up (g_signal_handlers_disconnect_by_data before dropping logind_proxy)."
  - "The known gap: stop() before on_bus_gotten leaves Power unregistered until restart."
design_challenger_required: true
architectural_task: false
design_review_result: APPROVE   # review 1: REVISE (addressed); review 2: APPROVE of the implementation (code only; runs on +unity8 required); R1 recorded as an unknown, R3 wording applied
```
