# UNITY-20261002-002: the power plugin's D-Bus object and name are never registered when stop() runs before on_bus_gotten

From UNITY-20260928-022 (its Design Challenger named the gap; the target
check of the +unity9 publication hit it). Agent A, target `target-desktop`,
2026-10-02. May's decision through C: fix forward as +unity10, no rollback.

## Mechanism (code, FACT)

`plugins/power/gsd-power-manager.c`:

- The plugin object creates its manager at load time
  (`GNOME_SETTINGS_PLUGIN_REGISTER`: `plugin_init` -> `gsd_power_manager_new`).
  `gsd_power_manager_new` creates the singleton `manager_object` once per
  process and calls `register_manager_dbus`, which queues
  `g_bus_get (G_BUS_TYPE_SESSION, priv->bus_cancellable, on_bus_gotten)`.
  `on_bus_gotten` registers `/org/gnome/SettingsDaemon/Power` and owns
  `org.gnome.SettingsDaemon.Power`. Nothing else ever registers them.
- `gsd_power_manager_stop` cancels and frees `priv->bus_cancellable` and
  frees `priv->introspection_data`. A GTask checks its cancellable when the
  result is collected, so a cancel at any point before `g_bus_get_finish`
  makes `on_bus_gotten` return on `G_IO_ERROR_CANCELLED` without registering.
- A later `gsd_power_manager_start` does not register: the plugin runs
  (inhibitors, idle, keys) with no D-Bus object and no name until the daemon
  restarts.
- Age: the cancel in `stop()` is in the archive's 0ubuntu6 (`ubuntu/devel`,
  since the 2014 import), in `unity/resolute`, +unity7 and +unity9. 27e75f4
  (+unity8) added a second cancel in `finalize` and did not touch `stop()`.

The only stop paths that leave the process alive are the plugin's own
deactivation (`plugin_enabled_cb` on the GSettings key
`com.canonical.unity.settings-daemon.plugins.power active`); `name_lost`,
`Stop`/`SessionOver` and exit all quit the main loop (`main.c`).

## The window at session start (measured)

`tools/u002-trace.bt` (bpftrace uprobes on `gsd_power_manager_new`,
`gsd_power_manager_start`, `gsd_power_manager_stop`, `on_bus_gotten`, run
from early boot by `tools/u002-trace.service`), 10 natural boots of the
published +unity9 (`runs/boots-unity9/`):

| boot | NEW -> ON-BUS-GOTTEN |
|---|---|
| 1..10 | 4209 - 6397 ms (median about 5.1 s) |

The result of `g_bus_get` is delivered only when the main loop runs again,
after every plugin's synchronous `start()`: at session start the window is
seconds, not the 90 ms seen on a warm `systemctl --user restart`
(`runs/restart-trace.txt`). Any stop of the power plugin in those seconds
loses the registration for the life of the process.

## Reproduction

- Deterministic (`tools/stop-before-bus.sh`, in UNITY-20260928-022
  `runs-race/`): u-s-d under gdb, `gsd_power_manager_stop` called after
  `start()` returns and before the bus result; then the plugin cycled with
  gsettings. +unity9 and +unity7 alike: no owner, Power calls ServiceUnknown,
  no crash; back under systemd the name is owned.
- Natural: 1 session start of 12 on the published +unity9 without test
  drop-ins (UNITY-20260928-022 `target-verification.md`): plugin running
  (logind inhibitors taken), no Power owner, NRestarts 0, no crash file. The
  10 boots traced here: 0 stops, name owned 10/10. What stopped the plugin in
  that session is **not known** (section below).

## What stopped the plugin at that session start (open)

Facts from that boot's journal (boot -11 of 2026-10-02, 18:42-18:45 EEST)
against the next good boot:

- same unit timings (u-s-d started 2.0 s before cinnamon-session, dconf
  service activated 4.3 s after u-s-d);
- the bad boot alone has four `compiz: failed to commit changes to dconf:
  Error receiving data: Socket operation on non-socket` at 18:43:31-35,
  inside u-s-d's plugin-start window (its xrandr plugin logged EDID at
  18:43:34);
- no "Name taken", no second u-s-d instance, no u-s-d warning, no
  `cinnamon-settings-daemon-*` autostart unit ran (all dead, OnlyShowIn
  X-Cinnamon), nothing in the system writes the `active` key
  (`10_ubuntu-settings.gschema.override` sets other power keys only); the
  key is stored `true` in the user db and defaults to `true`.

A documented path to `plugin_enabled_cb ("active")` at session start exists
(sweep, 2026-10-02): dconf's `dconf_engine_watch_established` emits a change
for every key under the watched path when another process's write lands
while a GSettings object's subscription is being set up ("SHM invalidated
while establishing subscription ... signalling change"; dconf 0.29.1 narrowed
it from "/" to the watched path, GNOME/dconf#41). compiz writes dconf in
that window. That gives a "changed" on `active`; a stop still needs the
read to return false, and the sweep found no path for that on a valid user
db (reads go through the lower sources only when the user gvdb fails to
open). So: a "changed" on `active` in the window is expected; the false
read is **not shown**. Further natural boots: `runs/boots-unity9-b/`.

## Existing fix: NOT_FIXED (sweep 2026-10-02, 20 min, read-only)

- gnome-settings-daemon: 3.8.6 has the same `register_manager_dbus` from
  `_new()` and the cancel in `stop()`; 9166afdb (2014, "power: Call stop from
  finalize", Ubuntu's LP: #1567116 fix) and the 2017 renames keep it. The
  case was removed structurally: caf51f50 (3.23.2, 2016) "main: Remove
  ability to start/stop individual plugins" - one process per plugin, stop()
  only at exit. 015fe8ef / a212e6d7 (2025, GApplication port, issue #867)
  move registration out of `_new()`. Neither is a fix we can carry: our
  daemon is the 3.8-era monolith with the `active` keys.
- unity-settings-daemon: no Launchpad bug for the missing Power name or dead
  brightness keys until restart (searches: brightness, power,
  SettingsDaemon.Power, no owner, not registered); LP: #1567116 is the crash
  in `stop()` on unload, fixed 2016. Archive: resolute 0ubuntu6; stonking
  26.10.1ubuntu.build1 (2026-09-22, no-change rebuild) - not checked for this
  code, same lineage.
- cinnamon-settings-daemon's csd-power: the same async `g_bus_get` from
  `_new()` with a cancel in `stop()`, but `stop()` runs only at process exit
  (daemon-skeleton): no re-start path, so the gap cannot happen there.
- Gaps: issue comment threads not readable (dconf#41, glib#2174, g-s-d #867);
  -proposed and PPAs not checked.

## Evidence card

```yaml
task_id: UNITY-20261002-002
package: unity-settings-daemon
target_series: resolute
issue: >-
  power plugin: D-Bus object and name never registered when stop() runs
  before on_bus_gotten (registration once per process, bus request
  cancelled in stop()); Power absent for the session
status: REPRODUCED   # deterministic under gdb on +unity7 and +unity9; natural 1 of 12 session starts on +unity9, trigger not identified
issue_search_result: PENDING   # sweep delegated 2026-10-02 (g-s-d upstream, Launchpad u-s-d, csd, dconf)
source_version: 15.04.1+21.10.20220802-0ubuntu6 (archive) and 0ubuntu7+unity9 (ours, published)
binary_version: measured on target-desktop, +unity9 from the repository and +unity7 from the repository
source_commit: code since the 2014 import; our published 57945f5 (+unity9)
observed: >-
  one session start of the published +unity9: u-s-d running, power plugin
  active (inhibitors taken), org.gnome.SettingsDaemon.Power has no owner,
  every Power call ServiceUnknown; systemctl --user restart fixes it.
  gdb: stop() between start() and the bus result reproduces it every time on
  +unity7 and +unity9.
expected: the Power object and name exist whenever the manager object exists; a stop/start cycle at any time keeps them
reproduction: tools/stop-before-bus.sh (UNITY-20260928-022 runs-race/01-04); window measured by tools/u002-trace.bt over 10 boots
existing_fix_result: PENDING
root_cause: >-
  register_manager_dbus runs once per process; stop() cancels its bus
  request; nothing re-registers on start()
root_cause_mechanism: >-
  GTask returns G_IO_ERROR_CANCELLED when its cancellable is cancelled before
  the result is collected; on_bus_gotten returns early; registration ids and
  name_id stay 0 for the process life
invariant: >-
  the power manager's D-Bus object and name live as long as the manager
  object, independent of start()/stop(); while stopped, calls get the
  "not running" error (UNITY-20260928-022)
chosen_approach: PENDING (Design Challenger before code)
regression_test: tools/stop-before-bus.sh (fail = no owner after stop before the bus result; pass = owner and an answered call), plus natural boots without drop-ins
```
