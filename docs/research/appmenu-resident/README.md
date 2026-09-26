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

## Re-check 2026-09-26: does a783b01c close every unload path? (agent B)

**The LP stack.** LP #2166410's gdb output shows
`dlclose` ← `g_module_close` ← libgtk-3, then a GDBus dispatch into unmapped
code. GTK 3.24.52 `gtk/gtkmodules.c`, `gtk_module_info_unref()`, drops a
module whose `ref_count` reaches 0 when the `gtk-modules` setting changes.
After a783b01c `g_module_make_resident()` makes that `g_module_close()` a
no-op, so the code stays mapped. That is exactly this stack.

**Neighbouring paths, from the source:**
- **Re-init.** When the module is added back to `gtk-modules`,
  `load_module()` does not find it in its list any more. It creates a new
  entry and calls `gtk_module_init()` again. With a resident module the
  statics survive, so a second `store_pre_hijacked()` would save the
  already-hijacked vfuncs as "pre-hijacked", and the hijacked realize would
  call itself.
  - This does not happen: `gtk_module_should_run()` has
    `static bool run_once`, which is false after the first run, so the
    second init does nothing.
- **The bus watcher** is also guarded (`watcher_id == 0`).
- **Other hooks.** The module exports only `gtk_module_init` and
  `g_module_check_init`, not `gtk_module_display_init`.
- **Other unloads.** It makes no `g_module_close`/`dlclose` of its own.
- **GTK2 and GTK4.** Our package builds the GTK3 module only; there is no
  GTK2 module, and GTK4 has no modules.
- **The parser library.** `libappmenu-gtk3-parser0` is an ordinary
  dependency and stays loaded while the resident module holds it.

**Measured** in a resolute chroot: Xvfb, xsettingsd, GTK 3.24.52,
`menuapp.py`, with the module only in `Gtk/Modules`, one display per run
(`readd.sh`).

| module | scenario | result |
|---|---|---|
| archive 25.04-1build1 | module dropped from the setting | SIGSEGV (139), 2 of 2 |
| ours +unity1 | kept | exit 0 |
| ours +unity1 | dropped | exit 0, module still mapped, menu-bar windows keep being created |
| ours +unity1 | dropped, then added back (re-init) | exit 0, 4 of 4; 6 ticks, windows with menu bars created after the re-add |

An earlier run showed "exit 1" once. That was the test itself: the next
run reused display :9 while the previous Xvfb was still exiting, and GTK
could not open the display. Each run now gets its own display.

**Conclusion.** a783b01c covers the reported stack, and no other unload or
re-init path is open; no further change is needed.

Still to do on target2, once it is back: run applications under Unity with
the module only in `gtk-modules`. The candidates are Chromium (a snap in
26.04; Chrome is not in the archive), GIMP 3 (GTK3) and LibreOffice (its
GTK3 VCL).

## Live check under Unity, 2026-09-26 (agent B)

target2 ran a Unity session from Clean-2, with GIMP 3.2.2 (archive),
LibreOffice 26.2.5 (gtk3 VCL) and Chromium 153.0.8010.47 (snap).

`live.sh` starts the three applications without `GTK_MODULES`, so the
module comes only from the `gtk-modules` XSETTING.
- The setting is u-s-d's
  `com.canonical.unity.settings-daemon.plugins.xsettings overrides`
  (`{'Gtk/Modules': <'appmenu-gtk-module'>}`).
- `enabled-gtk-modules` does not work for this: u-s-d only publishes the
  modules it knows.

The script then drops the module and adds it back, which is the KDE
scenario, run under Unity.

| module | GIMP 3.2.2 | LibreOffice Writer | Chromium snap |
|---|---|---|---|
| archive 25.04-1build1, 2 runs | module mapped; **SIGSEGV after the drop, 2 of 2** (`gimp-debug-tool`: "fatal error: Segmentation fault" for both pids) | module mapped; survives | module not mapped (the snap does not see host GTK modules); survives |
| ours +unity1, 2 runs | module mapped; **survives 2 of 2**, also after the re-add | survives | survives |

In the normal session, where the module comes from `GTK_MODULES`:
- **GIMP** exports its whole menu through the module:
  `_GTK_MENUBAR_OBJECT_PATH=/org/appmenu/gtk/window/N`, with File, Create,
  Open… as `unity.*` actions.
- **LibreOffice** exports its own native menu
  (`/org/libreoffice/window/…/menus/menubar`).

`+unity1` is in aptly since 2026-09-25; nothing changed.
