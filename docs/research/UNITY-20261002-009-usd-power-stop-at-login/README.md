# UNITY-20261002-009: what stops the power plugin at a session start

From UNITY-20261002-002 (the consequence, the lost D-Bus registration, is
fixed there by +unity10; this task is about the trigger). Not started;
this file holds the leads from -002 (agent A, 2026-10-02).

## The observation

One session start of the published u-s-d +unity9 on `target-desktop`
(boot of 2026-10-02 18:42-18:45 EEST, UNITY-20260928-022
`target-verification.md`): the power plugin running (its logind inhibitors
taken), NRestarts 0, no crash, but `org.gnome.SettingsDaemon.Power` had no
owner for the whole session; a `systemctl --user restart` fixed it. 19 traced
natural boots of +unity9 afterwards: no stop, Power owned 19/19
(`UNITY-20261002-002-usd-power-bus-race/runs/boots-unity9*`).

## Leads

1. **The stop ran inside the plugin-start phase, synchronously.** Measured in
   -002 (`runs/toggle-unity9-v2/`): a GSettings `active=false` written inside
   the window is dispatched by the main loop only after it resumes, and the
   `g_bus_get` completion queued at manager creation is dispatched first -
   every time (3/3, STOP 314-504 ms after ON-BUS-GOTTEN). So a key change
   handled by the main loop cannot have caused the bad boot. Whatever
   called `gsd_power_manager_stop` did so before the loop resumed: from
   within some plugin's `start()` that iterates the default main context
   (a nested `gtk_main`/`g_main_context_iteration`, a `*_sync` call that
   runs the loop), or a direct call. The stack of a stop is what
   `tools/u002-trace.bt` of -002 records (uprobe on `gsd_power_manager_stop`
   with `ustack`), so the tracer unit catches it if it recurs.
2. **The only stop paths that leave the process alive** are the plugin's
   own deactivation (`plugin_enabled_cb` on
   `com.canonical.unity.settings-daemon.plugins.power active`) and
   `gnome_settings_manager_stop`; `main.c`'s `stop_manager` always quits the
   main loop (`name_lost`, `Stop`, `SessionOver`). Check whether a nested
   loop makes `gtk_main_quit` quit only the inner level.
3. **The bad boot alone** had four `compiz: failed to commit changes to
   dconf: Error receiving data: Socket operation on non-socket` at
   18:43:31-35, inside u-s-d's start window. Same unit timings as a good
   boot otherwise; no second u-s-d instance, no "Name taken", no
   `cinnamon-settings-daemon-*` autostart ran.
4. **dconf's watch-established storm** (`dconf_engine_watch_established`,
   GNOME/dconf#41, 0.29.1): a change for every key of the watched path when
   another process writes during subscription setup - gives a "changed" on
   `active` at session start, but a stop needs the read to return false,
   and no path for that was found on a valid user db (-002 sweep).
5. Timing facts: at a cold session start the main loop is blocked for
   4-11 s in the plugin-start phase (`runs/boots-unity9*`); a quick
   false/true pair of writes in that time is read as the final value
   (`runs/toggle-unity9/`, 6/6 no stop); from a running session the same
   write stops the plugin within 250 ms.

Tools to reuse: `UNITY-20261002-002-usd-power-bus-race/tools/u002-trace.bt`
and `.service` (add a probe on `plugin_enabled_cb` and on
`gnome_settings_plugin_info_deactivate` in the main binary - check the
symbol with `bpftrace -l`), `boot-loop.sh`.
