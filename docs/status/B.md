# Agent B - running state

Test desktop: `target2` (192.168.56.30, VM `target-desktop-2`, snapshot `Clean-2`)
Build directory: `~/work/b`

## Now

**unity-gtk4-menu is agent B's package** (handed over by A, 2026-09-24).
0.4 released: menu items naming widget class actions work from the global
menu. Commit `ab81195` in `packages/unity-gtk4-menu`, built with sbuild,
published to aptly. Research and evidence: `research/layer-b/` ("Class
actions"); decision: DECISIONS 2026-09-24.

Breadth run with 0.4 done (17 applications) and the HUD route verified; see
`research/layer-b/` ("Breadth with 0.4"). Proposed next, not started:
menu selection by `primary` then by `app.`/`win.` share; a trigger for
gjs/PyGObject applications; menus built after realize.

## State of `target2`

Dirty (`~/.dirty`): `libunity-gtk4-menu0` 0.4 installed with `dpkg -i`
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
