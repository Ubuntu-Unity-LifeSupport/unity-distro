# Layer B: what a GTK4 global menu actually needs

Measured on target, Ubuntu Unity 26.04, GTK4 4.22.4, 2026-09-23. Everything
here is an experiment, not a reading of documentation.

## The handoff's assumption was wrong in both directions

§3 of the handoff describes Layer B as "one patch exporting popover menu models
from GTK4, which gives the global menu and the HUD to every libadwaita
application at once". Two things are off.

**Worse than assumed: there is no way to deliver such a patch to applications.**
GTK4 has no module loading mechanism at all. Checked directly in the shipped
libraries:

| Symbol / string | libgtk-3.so.0 | libgtk-4.so.1 |
|---|---|---|
| `GTK_MODULES` | present | absent |
| `gtk_module_init` | present | absent |
| `gtk-modules` | present | absent |

`appmenu-gtk-module` works by being loaded into every GTK3 process through
`GTK_MODULES` and overwriting `realize` in the `GtkWindow`, `GtkApplicationWindow`
and `GtkMenuBar` class vtables. None of that is available under GTK4. Patching
`appmenu-gtk-module` for GTK4, which is what the handoff implies, cannot work -
it builds only `src/gtk-2.0` and `src/gtk-3.0`, and there is nothing to build a
`gtk-4.0` against.

**Better than assumed: the export machinery is intact and Unity already
supports it.** Stock, unpatched GTK4 still exports a menubar over
`org.gtk.Menus` and advertises it through X11 window properties. `mbtest.c` is
a twenty-line GTK4 application whose only unusual act is calling
`gtk_application_set_menubar()`. Its window carries:

```
_GTK_MENUBAR_OBJECT_PATH     = "/org/unitydistro/mbtest/menus/menubar"
_GTK_APPLICATION_OBJECT_PATH = "/org/unitydistro/mbtest"
_GTK_UNIQUE_BUS_NAME         = ":1.104"
```

and the model is readable on the bus:

```
$ gdbus call --session --dest :1.104 \
    --object-path /org/unitydistro/mbtest/menus/menubar \
    --method org.gtk.Menus.Start "[0]"
([(0, 0, [{'label': <'TestFile'>, ':submenu': <(1, 0)>},
          {'label': <'TestHelp'>, ':submenu': <(2, 0)>}])],)
```

**The Unity panel displays it.** Screenshot:
`../../screenshots/2026-09-23-gtk4-menu-in-unity-panel.png`. Hovering the panel
shows `TestFile  TestHelp`. No patched package was involved.

So the transport works end to end today. What is missing is only that real
applications never call `set_menubar`: they hang their menu on a
`GtkMenuButton` inside an `AdwHeaderBar`.

## The constraint that shapes any fix

`latetest.c` is the same application, except the menubar is attached six
seconds after the window is presented. Result: `_GTK_MENUBAR_OBJECT_PATH` is
never set, and the panel shows only the window title.

**The menubar has to be in place before the window is realized.** Anything
acting from outside the application has to get in before that moment, which
rules out the simplest approach of walking existing windows and attaching a
menu after the fact.

## What this makes the job

Not a GTK4 fork. Roughly:

1. Get into GTK4 processes before window realize. There is no module hook, so
   the remaining route is symbol interposition via `LD_PRELOAD`. There is a
   working precedent in this very session: `libgtk-nocsd.so.0` is already
   preloaded into the Unity session to suppress client-side decorations.
2. At that point find the window's header bar menu button and read its model.
   `gtk_menu_button_get_menu_model()` and `gtk_popover_menu_bar_get_menu_model()`
   are public API, so no private headers and no GTK internals are needed.
3. Hand it to `gtk_application_set_menubar()` before realize completes.

Open question for step 2: whether the application has populated the menu button
that early. If it has not, the shim needs to defer, and deferring is exactly
what `latetest.c` shows does not work - which would push the fix back into GTK4
itself.

## A GTK4 bug candidate, noted in passing

`gtk_application_set_menubar()` called after the window is realized silently
does nothing on X11: no property is set and no error is raised. Whether that is
intended is worth asking upstream. It is not our bug to fix and it does not
travel with any patch of ours.

## Reproducing

```bash
gcc mbtest.c   -o mbtest   $(pkg-config --cflags --libs gtk4)
gcc latetest.c -o latetest $(pkg-config --cflags --libs gtk4)
```

Run on target with `DISPLAY=:0` and the session's `DBUS_SESSION_BUS_ADDRESS`,
then `xprop -id $(xdotool search --name '^mbtest$')`.
