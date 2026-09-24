# Agent B - running state

Test desktop: `target2` (192.168.56.30, VM `target-desktop-2`, snapshot `Clean-2`)
Build directory: `~/work/b`

## Now

**nux 0ubuntu15+unity2** (2026-09-24): `fix-fbo-attachment-arrays.patch`
(LP #2160298), branch `b/fbo` (`9793c23`), in aptly; `research/nux-fbo/`.
target2 runs it. The `b-nux` chroot has +unity2 installed and autotools added.

**indicator-bluetooth, indicator-printers** - agent B's since 2026-09-24.
`+unity1` in aptly (systemd-dev, unit restored); branches `unity/resolute`
in `packages/`, patches in `research/indicator-units/`. target2 has both
installed with `dpkg -i`.

**calamares-settings-ubuntu** - agent B's since 2026-09-24 (known issue #4,
May approved). `1:26.04.12+unity1` in aptly (`-ubuntu-unity`, `-common`,
`-common-data`): basicwallpaper is a desktop window on X11, so it cannot cover
Calamares in the OEM first-time setup. Commit `b6b546b`, branch
`unity/resolute` of `packages/calamares-settings-ubuntu` (no remote of ours -
patch and notes in `research/calamares-oem/`). Confirmed on a real OEM
install in VM `oem-test` (192.168.56.105 by DHCP, MAC 08:00:27:FC:1D:99;
`ssh oemtest` in ~/.ssh/config). Its state now: end-user setup finished,
user `tester` / `endusertest-2604`, `oem` removed. Snapshot `OEM-ready`
(host) is the state before the end user's first boot, `OEM-ready-fixed` the
same with our basicwallpaper; oem-test currently runs `OEM-ready-fixed`'s
first boot. The black screen seen at the OEM-preparation Unity login was
not agent A's gvfs race (its journal, boot -1 on the `OEM-ready` disk: gvfs
started in 1.8 s, never cancelled); it was a slow first start, ~51 s from
autologin to compiz, told to A; OEM user there is
`oem` / `oemtest-2604`, with openssh-server and B's key added. Test-VM
passwords only.

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

May is switching it off for now (2026-09-24). **Before the next `apt update` there: check
`timedatectl`** - target's clock was 1 h 07 min slow on 2026-09-24 (NTP
unreachable), and apt rejected our InRelease as "not valid yet" (agent A).
Pending there: `apt upgrade` from aptly brings unity +unity8, compiz +unity2,
gtk-nocsd +unity2 (agent A). Agent A already checked unity-gtk4-menu 0.8
with those on target (preload order as environment.d builds it):
gnome-characters (gjs) and gnome-text-editor run, both libraries mapped, no
crash, global menu in the panel for both. One `Gtk-WARNING AdwHeaderBar
reported min width -2` from gnome-characters comes from gtk-nocsd, not the
shim (agent A: gtk-nocsd alone 2, both 2, no preload 0). Harmless. Added for #4: `calamares`,
`calamares-settings-ubuntu-unity` (archive 26.04.12), `xvfb`, `x11-apps`,
`imagemagick`; `/tmp/oemcfg` (unpacked `oemconfig.tar.gz`), `~/b/proto/`,
`~/b/oemenv.sh`, `stack.sh`, `check.sh`, `race.sh`.
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

- `/var/tmp/sbuild-claude/b-dev` - now also has Qt6 dev, Xvfb, xfwm4,
  Calamares and our calamares-settings-ubuntu-unity `+unity1`, for
  `research/calamares-oem/check.sh`.
- `~/work/b/iso` - ISO manifest, calamares-settings-ubuntu 26.04.12 source,
  `www/` (bootstrap for `oem-test`, served by tmux `b-www`).
- `/var/tmp/sbuild-claude/b-nux` - chroot with our nux, Xvfb, Xorg dummy and
  TigerVNC, for `research/nux-vidmode/`.
- `~/work/b/nux/` - nux build output and test programs.

- `~/work/b/src/` - yelp 49.0 and gtk4 4.22.4 sources (read-only reference).
- `~/work/b/out/` - 0.4 source and binary packages, sbuild log.
- `/var/tmp/sbuild-claude/b-dev` - dev chroot with `libgtk-4-dev`, entered
  with `sudo unshare --mount --pid --fork chroot`.
