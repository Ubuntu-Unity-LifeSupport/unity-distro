# appmenu-gtk3-module: GTK3 unloads it and the app segfaults (LP: #2166410)

Found by the stack-health sweep (`docs/STACK-HEALTH.md`, row appmenu-gtk-module).
Reported 2026-09-03 for Chrome 152 on KDE Plasma with the global menu.
Fixed upstream in vala-panel-appmenu commit
[a783b01c](https://gitlab.com/vala-panel-project/vala-panel-appmenu/-/commit/a783b01c8b653349843fac9bbd075dac52cdc9de)
("gtk-module: make the module resident", 2026-09-04), not in any release
(last 25.04), not in Debian or Ubuntu.

## When it can happen - and why not in our session by default

GTK 3.24.52 `gtk/gtkmodules.c`: modules named in `GTK_MODULES` are loaded once
and their references deliberately leaked ("always loaded"); modules loaded
through the `gtk-modules` setting (XSETTINGS `Gtk/Modules`) are unreffed and
`g_module_close()`d when the setting changes. appmenu-gtk-module hijacks the
GtkMenuBar class and keeps a bus-name watcher, so once unmapped the next
menu-bar call or D-Bus callback jumps into freed code.

In our Unity session the module comes from `GTK_MODULES=appmenu-gtk-module:gail:atk-bridge`
(compiz's environment on target2), and u-s-d publishes
`Gtk/Modules = canberra-gtk-module:gail:atk-bridge` - no appmenu module. So
the default Unity session cannot hit this; KDE, which puts the module in
`Gtk/Modules`, can. The fix is protection for anyone who loads it the other
way.

## Reproduction (target2, Xvfb :9, xsettingsd as XSETTINGS manager)

`unload.sh MODE` starts `menuapp.py` (a GTK3 window that builds another
menu-bar window every 3 s), then after 6 s drops the module from `Gtk/Modules`:

| Module | Loaded via | Result |
|---|---|---|
| archive 25.04-1build1 | `Gtk/Modules` only | **segfault** (exit 139) right after the change |
| archive 25.04-1build1 | `GTK_MODULES` (as in Unity) | stays mapped, runs to the end |
| ours +unity1 | `Gtk/Modules` only | stays mapped, runs to the end (exit 0) |

## Fix

`2001_make-module-resident.patch` = upstream a783b01c (path adjusted): a
`g_module_check_init()` that calls `g_module_make_resident()`. Package
`appmenu-gtk-module 25.04-1build1+unity1`, branch `unity/resolute` of
`packages/appmenu-gtk-module` (git-ubuntu clone, no remote of ours), in
aptly: appmenu-gtk3-module, appmenu-gtk-module-common,
libappmenu-gtk3-parser0 and the two -dev packages.

## Verified on target2

- `nm -D` shows `g_module_check_init` exported by the new module.
- Installed with dpkg: a GTK3 window with a GtkMenuBar in the real Unity
  session exports its menu (`_GTK_MENUBAR_OBJECT_PATH`,
  `_UNITY_OBJECT_PATH` = `/org/appmenu/gtk/window/0`), "File" shows in the
  panel, no menu bar inside the window; no new crash reports.
- Not checked: opening the menu from the panel by click (the scripted click
  missed), Chrome itself.
