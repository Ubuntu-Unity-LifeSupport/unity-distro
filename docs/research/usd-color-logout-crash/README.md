# unity-settings-daemon crash at logout (color plugin)

Fixed in unity-settings-daemon `15.04.1+21.10.20220802-0ubuntu7+unity2`, in
aptly, https://github.com/Ubuntu-Unity-LifeSupport/unity-settings-daemon.
This is the "libcolor crash at restart" noted earlier and closed as a probable
consequence of the compiz exit crash - it was not.

## Symptom

A crash report of `unity-settings-daemon` after logging out (found in
`/var/crash` after the login-race test, 2026-09-24 23:21). SIGSEGV
(`runs/00-logout-crash-backtrace.txt`):

```
#0 cd_client_get_connected ()                       libcolord
#1 gcm_session_active_changed_cb (session, ..., manager)   plugins/color
#6 <emit signal 'g-properties-changed'>
#7 on_name_owner_changed ()                          gio: the session manager left the bus
#12 g_main_loop_run / gtk_main
```

## Cause

`gsd_color_manager_init()` connects `gcm_session_active_changed_cb` to
"g-properties-changed" on the session manager proxy. That proxy is shared by
all plugins (`gnome_settings_bus_get_session_proxy()`, a static singleton).
`gsd_color_manager_stop()` clears the manager's colord client and its
reference to the proxy but leaves the handler connected; `finalize()` then
disconnects by data from `priv->session`, which `stop()` already set to NULL,
so it disconnects nothing. Any later property change of the session manager
calls into a stopped manager, and after finalize into freed memory. At
logout the session manager leaves the bus while unity-settings-daemon shuts
down.

Measured with gdb on target (`runs/usd-gdb.sh`): switch the plugin off
(`com.canonical.unity.settings-daemon.plugins.color active false`, which
calls `stop()`), then take and release an inhibitor through
`org.gnome.SessionManager.Inhibit` - two `PropertiesChanged` (InhibitedActions).
`+unity1`: `STOP`, then two `CB ... client=(nil)` (libcolord's
`CD_IS_CLIENT` check catches NULL, freed memory is not caught;
`runs/01-unity1-gdb.txt`). `+unity2`: `STOP`, no callback
(`runs/02-unity2-gdb.txt`).

## Fix

Disconnect in `stop()`, and connect with `g_signal_connect_object`, as
gnome-settings-daemon did for the same shared proxy in
[fb2ca61f](https://gitlab.gnome.org/GNOME/gnome-settings-daemon/-/commit/fb2ca61f40ea7ba94fdf3bf579e80fc3700867af)
(2019); `finalize()` checks for NULL. Upstream never had an explicit
disconnect: the problem left gnome-settings-daemon through refactors
(09f2cf1b, 2013) and the callback was deleted in 97250025 (2021).
unity-settings-daemon `ubuntu/devel` still has it. No bug on Launchpad or
GNOME GitLab (searched for `gcm_session_active_changed_cb` and
`cd_client_get_connected`, all statuses).

Verified: the gdb test above, and 4 logout cycles run by root
(`../compiz-restart/runs/logout/lo-root.sh`) with no crash, no
`CD_IS_CLIENT` critical, `/var/crash` empty (`runs/03-unity2-logout-cycles.txt`).
Before: 1 crash in about 13 logouts - too rare to prove a fix by counting;
the gdb test is the proof.

## Restart after switching off - fixed in `+unity3`

`init()` created the colord client, the session proxy, the profile store,
the settings and the caches; `stop()` destroys them. Switched off and on
(the `active` key), the plugin started with all of them NULL and did nothing
until unity-settings-daemon was restarted. Now they are created at the start
of each `start()`; `init()` keeps the root window.

Measured under gdb (`runs/usd-color-restart.sh`: switch off, switch on, watch
`stop`, `start` and `gcm_session_client_connect_cb`):
`+unity2` - STOP, START, no colord connection, `cd_client_connect: assertion
'CD_IS_CLIENT (client)' failed` (`runs/04-restart-unity2.txt`);
`+unity3` - STOP, START, COLORD-CONNECTED, twice in a row, no critical, the
display still registered in colord (`runs/05-restart-unity3.txt`). The
logout fix re-checked on `+unity3`: no callback after STOP.
