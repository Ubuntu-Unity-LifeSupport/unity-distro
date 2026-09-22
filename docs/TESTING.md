# Testing on target

`target` is the throwaway desktop VM: Ubuntu Unity 26.04, user `mike`,
192.168.56.20, reachable as `ssh target`. Its clean snapshot is called
`Clean`, capital C.

## Before installing anything

```bash
ssh target 'touch ~/.dirty'
```

Ask May for a rollback, then verify it yourself - the machine answers and the
marker is gone:

```bash
ssh target 'ls ~/.dirty'
```

## Screenshots - your eyes on the desktop

No sudo and no extra packages needed; `gnome-screenshot` ships with the
desktop.

```bash
ssh target 'DISPLAY=:0 gnome-screenshot -f /tmp/shot.png'
scp target:/tmp/shot.png ~/shots/$(date +%F-%H%M).png
```

**Do not use `xwd -root` or `import -window root` for the desktop.** They read
the X11 root window, which under Compiz holds no wallpaper - you get a black
background with a perfectly good panel on top, which looks like a bug and is
not one. They are still fine for individual windows. See DECISIONS.md.

Before reporting anything you saw only in a screenshot, ask May whether the
physical screen shows the same thing.

For the greeter rather than a logged-in session, run as the `lightdm` user with
its `XAUTHORITY`.

Save anything that documents a real change to `docs/screenshots/YYYY-MM-DD-*.png`.

## Driving the desktop from builder

`xdotool` on target turns the checklist into a script - no need to sit at the
machine:

```bash
xdotool key super          # Dash
xdotool key alt            # HUD
xdotool mousemove 1253 14 click 1   # session indicator
xdotool mousemove 1159 14 click 1   # sound indicator
```

Export `DISPLAY=:0` plus `DBUS_SESSION_BUS_ADDRESS` and `XDG_RUNTIME_DIR` taken
from `/proc/$(pgrep -x compiz)/environ`, or nothing will reach the session.

Two things a screenshot cannot answer, so ask May: whether the mouse cursor is
visible, and whether anything feels laggy.

## Measuring the global menu objectively

Do not judge the global menu by eye. Ask the registrar what is registered:

```bash
gdbus call --session --dest com.canonical.AppMenu.Registrar \
  --object-path /com/canonical/AppMenu/Registrar \
  --method com.canonical.AppMenu.Registrar.GetMenus
```

Baseline taken 2026-09-22 with `file-roller`, a GTK3 headerbar application:

```
([(uint32 48234500, '', objectpath '/')],)
```

The window is registered, the service name is empty and the object path is `/`
- the plumbing is connected and there is no menu model behind it. A Layer B
patch succeeds when that entry carries a real service name and path.

## Reproducing the shutdown menu bug

The 26.04 note reads "shutdown/logout menu not working **after cancelling**".
The precondition is the whole bug; opening the menu once proves nothing.

1. session indicator -> "Выключение..."
2. cancel the dialog - it has no Cancel button, so either `Escape` or the close
   cross at its top left
3. open the session indicator again and try "Выключение..." or "Завершение
   сеанса"

Both cancel routes were tried on 2026-09-22 and the bug did not appear. The
logout path has not been tested.

## Manual checklist

Run the whole list after any change to the shell, the session or the
indicators:

- [ ] log in through `unity-greeter`
- [ ] cursor is visible after login
- [ ] panel renders
- [ ] launcher renders and responds
- [ ] Dash opens
- [ ] global menu appears for a GTK3 application
- [ ] HUD opens on Alt
- [ ] indicators work: network, sound, session
- [ ] shutdown menu works, and the dialog appears exactly once
- [ ] wallpaper is drawn

Record what you saw in `docs/STATUS.md`, not only what you fixed.
