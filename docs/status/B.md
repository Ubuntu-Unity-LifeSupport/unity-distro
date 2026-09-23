# Agent B - running state

Test desktop: `target2` (192.168.56.30, VM `target-desktop-2`, snapshot `Clean-2`)
Build directory: `~/work/b`

## Now

**unity-gtk4-menu is agent B's package** (handed over by A, 2026-09-24).
Released: 0.4 (class action stand-ins, `ab81195`) and 0.5 (main menu choice,
`c0557df`), both built with sbuild and published to aptly. Nothing in flight.

Proposed next, none started - May decides: a load trigger for gjs/PyGObject
applications; menus built after realize (font-viewer, contacts); enabled state
for stand-ins (interposing `gtk_widget_action_set_enabled`, which applications
call through the PLT), which would also fix `hidden-when` pairs.

## State of `target2`

Dirty (`~/.dirty`): `libunity-gtk4-menu0` 0.5 installed with `dpkg -i`
(session-wide, rebooted), `xdotool` and 14 GTK4 test applications from the
archive (`--no-install-recommends`), test files in `~/b/`
(`run.sh`, `inspect.sh`, `audit.py`, `breadth.sh`, `classtest`, 0.3, 0.4
and probe `.so`). No aptly source
configured. Pre-existing `/var/crash/_usr_bin_light-locker.1000.crash` is the
archive's known issue #5, from before any change.

## Mine outside git

- `~/work/b/src/` - yelp 49.0 and gtk4 4.22.4 sources (read-only reference).
- `~/work/b/out/` - 0.4 source and binary packages, sbuild log.
- `/var/tmp/sbuild-claude/b-dev` - dev chroot with `libgtk-4-dev`, entered
  with `sudo unshare --mount --pid --fork chroot`.
