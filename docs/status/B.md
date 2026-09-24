# Agent B - running state

Test desktop: `target2` (192.168.56.30, VM `target-desktop-2`, snapshot `Clean-2`)
Build directory: `~/work/b`

## Now

**nux** - agent B's since 2026-09-24. `0ubuntu15+unity1` in aptly: upstream
0ubuntu15 (ICU in place of Unicode-licensed code, no boost-system) plus our
`fix-missing-vidmode.patch`; commit `9d26778`, branch `b/ubuntu15` of
`packages/nux` (no remote of ours - patch and notes in
`research/nux-vidmode/`). Unity's unit tests pass on it under plain Xvfb
(agent A). Found: upstream's ICU conversions are broken but unused on Linux.

**unity-gtk4-menu is agent B's package** (handed over by A, 2026-09-24).
Released 0.4-0.8, all in aptly. Nothing open.

Qt global menu: measured, already works (Qt5, Qt6, KDE) - nothing to build.

Proposed next, none started - May decides: whether to report the two
gtk-nocsd findings and nux's broken ICU conversions upstream (on hold).

## State of `target2`

Dirty (`~/.dirty`): libnux `0ubuntu15+unity1` (was archive 0ubuntu12) and
`libunity-gtk4-menu0` 0.8 installed with `dpkg -i`
(session-wide, rebooted), `xdotool`, 18 GTK4 test applications (C, gjs, Python) and 3 Qt ones
(featherpad, kcalc, speedcrunch) from the archive (`--no-install-recommends`), `org.gnome.Contacts did-initial-setup` true
(set by completing contacts' setup), test files in `~/b/`
(`run.sh`, `inspect.sh`, `audit.py`, `breadth.sh`, `classtest`, 0.3, 0.4
and probe `.so`). No aptly source
configured. Pre-existing `/var/crash/_usr_bin_light-locker.1000.crash` is the
archive's known issue #5, from before any change. Crash reports from
our experiments are moved, not deleted, to `~/b/crash-before-0.6/` and
`~/b/crash-0.6/`, `~/b/crash-0.7/` - all accounted for in `research/layer-b/`.

## Mine outside git

- `/var/tmp/sbuild-claude/b-nux` - chroot with our nux, Xvfb, Xorg dummy and
  TigerVNC, for `research/nux-vidmode/`.
- `~/work/b/nux/` - nux build output and test programs.

- `~/work/b/src/` - yelp 49.0 and gtk4 4.22.4 sources (read-only reference).
- `~/work/b/out/` - 0.4 source and binary packages, sbuild log.
- `/var/tmp/sbuild-claude/b-dev` - dev chroot with `libgtk-4-dev`, entered
  with `sudo unshare --mount --pid --fork chroot`.
