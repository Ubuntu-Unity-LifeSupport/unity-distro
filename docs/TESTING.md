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
