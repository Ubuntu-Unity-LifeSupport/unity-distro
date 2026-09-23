# Testing on target

`target` is the throwaway desktop VM: Ubuntu Unity 26.04, user `mike`,
192.168.56.20, reachable as `ssh target`.

## Snapshots

Rebuilt 2026-09-23. The old layout is gone.

```
Clean                         base: clean system + autologin + passwordless sudo
 └─ Clean-updated-2026-09-23  + all pending updates.  ROLL BACK TO THIS ONE
```

`Clean` is permanent and not to be touched. Note that its contents changed: the
original as-installed snapshot was deleted and `Clean-autologin` was renamed to
`Clean`, so the name is the same and the contents are not.

**Test on the updated snapshot, not on release state.** Two reasons: SRU
verification does not formally count on release state, and we have twice chased
ghosts on stale systems - the PCRE2 fix had existed for six months, and the
shutdown menu did not reproduce. All five known 26.04 bugs were described at
release, and some may have closed since.

The updated snapshot ages. When it falls behind: roll back to it, catch up on
updates, take a new one with a new date, and **delete the previous one** - a
long snapshot chain slows disk I/O.

Autologin and passwordless sudo live in `Clean`, underneath the updates, so
every snapshot taken further down the chain inherits them. They never need
re-enabling after a rollback.

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

Write the script to a file on target and run it, rather than passing it inline.
`pkill -f <name>` run inline over ssh matches the ssh command's own command
line, which contains that name, and kills the shell running it.

## Powering target off from outside

**`VBoxManage controlvm acpipowerbutton` does not turn target off - but it is
not ignored either.** It opens a confirmation dialog, owned by
`cinnamon-session-quit`, and waits for someone to answer it. With nobody at the
screen the VM stays running indefinitely while `VBoxManage` reports success.
That once left a host-side wait loop spinning for over a day, poised to roll
target back at a random later moment.

The session is behind it, not the VM: `unity-settings-daemon` holds a blocking
logind inhibitor on `handle-power-key`, and its power-button action is
`interactive`. Designed desktop behaviour, not a bug.

To power off for a rollback, shut down from inside:

```bash
ssh target 'sudo -n systemctl poweroff'
```

## Getting file contents onto target intact

Send them **base64-encoded** and check the result with `cat -A`, not `cat`.

Quoting does not survive two shell parses, and a config written through nested
ssh can arrive as one line with literal `\n` in it. That happened to the
autologin config: `"[Seat:*]nautologin-user=mikenautologin-user-timeout=0n"`.
`cat` renders a broken file and a correct one identically; `cat -A` shows line
endings as `$` and makes the difference obvious.

A broken file caught late is worse than one caught early: had that config gone
into the base snapshot, autologin would have failed mysteriously after every
rollback and the search would have started at LightDM.

Two things a screenshot cannot answer, so ask May: whether the mouse cursor is
visible, and whether anything feels laggy.

## Measuring the global menu objectively

Do not judge the global menu by eye. Ask the registrar what is registered:

```bash
gdbus call --session --dest com.canonical.AppMenu.Registrar \
  --object-path /com/canonical/AppMenu/Registrar \
  --method com.canonical.AppMenu.Registrar.GetMenus
```

Baseline taken 2026-09-22 with `file-roller`, a GTK4 + libadwaita header bar application:

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

The full, corrected list of six known 26.04 bugs with their release-note
workarounds is in `UNITY-DISTRO-HANDOFF.md` §2.

## Manual checklist

Run the whole list after any change to the shell, the session or the
indicators:

- [ ] log in through `unity-greeter`
- [ ] cursor is visible after login
- [ ] panel renders
- [ ] launcher renders and responds
- [ ] Dash opens
- [ ] global menu appears for a **GTK3** application - use `gedit`, `synaptic`,
      `gnome-terminal`, `pluma` or `caja`. Not the file manager: nautilus is
      GTK4 + libadwaita in 26.04, so it tests a path that is not there yet
- [ ] **GTK4 + libadwaita branch** (`nautilus`, `file-roller`,
      `gnome-text-editor`, `gnome-calculator`): the window carries
      `_GTK_MENUBAR_OBJECT_PATH` in `xprop`, the registrar query above lists it,
      the menu appears on hovering the panel, and its items are found by the HUD
- [ ] HUD opens on Alt
- [ ] indicators work: network, sound, session
- [ ] shutdown menu works, and the dialog appears exactly once
- [ ] wallpaper is drawn

Record what you saw in `docs/STATUS.md`, not only what you fixed.
