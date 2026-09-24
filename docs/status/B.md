# Agent B - running state

Test desktop: `target2` (192.168.56.30, VM `target-desktop-2`, snapshot `Clean-2`)
Build directory: `~/work/b`

## Now

**unity-gtk4-menu is agent B's package** (handed over by A, 2026-09-24).
Released: 0.4 (class action stand-ins, `ab81195`), 0.5 (main menu choice,
`c0557df`), 0.6 (gjs/Python through `g_module_symbol`, `0ce1eb1`), 0.7
(enabled state of stand-ins, `4380c4d`), 0.8 (property actions as check and
radio items, `b625153`), all built with sbuild and published to aptly.
Nothing in flight.

"Menus built after realize" turned out not to exist (font-viewer has no
menu; contacts shows a setup window first) - nothing shipped, unshipped diff
kept in `research/layer-b/`.

Proposed next, none started - May decides: whether to report the two
gtk-nocsd findings upstream (May has said to hold upstream work for now, per
agent A - to confirm with May).

## State of `target2`

Dirty (`~/.dirty`): `libunity-gtk4-menu0` 0.8 installed with `dpkg -i`
(session-wide, rebooted), `xdotool` and 18 GTK4 test applications (C, gjs, Python) from the
archive (`--no-install-recommends`), `org.gnome.Contacts did-initial-setup` true
(set by completing contacts' setup), test files in `~/b/`
(`run.sh`, `inspect.sh`, `audit.py`, `breadth.sh`, `classtest`, 0.3, 0.4
and probe `.so`). No aptly source
configured. Pre-existing `/var/crash/_usr_bin_light-locker.1000.crash` is the
archive's known issue #5, from before any change. Crash reports from
our experiments are moved, not deleted, to `~/b/crash-before-0.6/` and
`~/b/crash-0.6/`, `~/b/crash-0.7/` - all accounted for in `research/layer-b/`.

## Mine outside git

- `~/work/b/src/` - yelp 49.0 and gtk4 4.22.4 sources (read-only reference).
- `~/work/b/out/` - 0.4 source and binary packages, sbuild log.
- `/var/tmp/sbuild-claude/b-dev` - dev chroot with `libgtk-4-dev`, entered
  with `sudo unshare --mount --pid --fork chroot`.
