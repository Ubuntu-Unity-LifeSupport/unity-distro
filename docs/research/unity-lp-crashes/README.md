# Two Launchpad crash reports in unity: LP #2160299, LP #2165662

Found by the stack-health survey (`../../STACK-HEALTH.md`): two crash reports
filed after 26.04's release, each with a patch, neither merged upstream
(merge proposal 508187 for #2160299 "Needs review"; no commit on gitlab
`ubuntu-unity/unity` `ubuntu/devel` since June). Both reproduced on our
`+unity8`, fixed in unity `+unity9` (in aptly), with the reporters' patches.

## LP #2160299 - compiz crashes at every start with an unknown default file manager

`FileManager::GetDefault()` returned an empty pointer when the default handler
for `inode/directory` was neither Nautilus nor Nemo. `TrashLauncherIcon`
connects to its signals when the launcher is built:
`sigc::signal_base::connect` ← `StorageLauncherIcon` ← `TrashLauncherIcon (fm=empty)`
← `launcher::Controller::Impl` (`runs/03-lp2160299-unity8-backtrace.txt`).

Reproduced with a test `.desktop` made the default (`runs/fm-default.sh`):
on `+unity8`, `killall -1 compiz` put unity7.service through **nine core dumps
in a row** until the default was set back - no session at all. On `+unity9`:
compiz restarts, no crash.

Fix: fall back to Nemo, as the function already did when there is no default.
Based on Riku's patch in the bug.

## LP #2165662 - compiz crashes on shaped override-redirect windows (Wine menus)

`ComputeShapedShadowQuad()` drops `shaped_shadow_pixmap_` when the window's
shape is empty but keeps `last_shadow_rect_`; when the shape comes back at the
same size the rebuild is skipped and the null pixmap is dereferenced.

Reproduced with `runs/shaped-flicker.c` - an override-redirect window mapped
and unmapped 200 times, its shape alternating between a region and nothing:
on `+unity8` compiz crashed in 2 runs of 3, in `SimpleTexture::texture
(this=0x0)` from `ComputeShapedShadowQuad` (DecoratedWindow.cpp:792,
`runs/01-lp2165662-unity8-backtrace.txt`). On `+unity9`: 3 runs of 3, no
crash (`runs/02-unity9-both-reproducers.txt`).

Fix: OldSamuray's patch from the bug - rebuild when there is no pixmap,
return if building failed. Not the same bug as our `+unity8` fix (generic
shadow path, empty inactive texture); this is the shaped path.

## Found on the way: unity-settings-daemon crash at logout

`/var/crash` on target also held a unity-settings-daemon crash from one of the
login-race test logouts (2026-09-24 23:21). Backtrace:
`cd_client_get_connected` ← `gcm_session_active_changed_cb` ←
`g-properties-changed` on the session proxy. `gsd_color_manager_stop()` clears
`priv->client` and drops its reference to the session proxy without
disconnecting its handler; the proxy is shared by all plugins
(`gnome_settings_bus_get_session_proxy`, static), outlives the stop, and at
logout - the session manager leaving the bus - calls back into a stopped
manager. This is the "libcolor crash at restart" noted before. Fixed in unity-settings-daemon `+unity2`: `../usd-color-logout-crash/`.
Also: the logout cycles did not check `/var/crash` after logout for
unity-settings-daemon; "no crash" in `../compiz-restart/` held for compiz,
not for every process.
