# Agent B - running state

Test desktop: `target2` (192.168.56.30, VM `target-desktop-2`, snapshot `Clean-2`)
Build directory: `~/work/b`

## Now

**Global menu gaps** (2026-09-26, May via the coordinator): `research/nocsd-gaps/`.
- (a) now covers inserted action groups: 10 dead items to 0.
- New part (d): late menus, live changes, shown menu buttons (Pinta,
  Papers, Console, Nautilus).
- GTK3, button hiding and per-window menus estimated only.
- Gir.Core apps do not trigger the types bug.
- gtk-nocsd main crashes Epiphany (not ours, not reported).
- Five-commit series on branch `split-parts-2` in `~/work/b/nocsd-up/split`
  (local); nothing sent. target2 rolled back to Clean-2 (checked inside).

**gtk-nocsd is B's as a whole since 2026-09-26** (May, via the coordinator):
- the package (`packages/gtk-nocsd`, branch `unity/resolute`, handed over by A);
- the global menu patch (`research/nocsd-upstream/`, `nocsd-reply2/`,
  `nocsd-gaps/`);
- the upstream findings. Epiphany aborts on main when opening Passwords:
  first bad commit 8f076dd, reproducer and fix in
  `research/nocsd-epiphany-crash/`, not sent.

Our aptly carries 4.8, which is not affected.
`4.8-1+unity2` adds `/etc/X11/Xsession.d/51gtk-nocsd`, so Xfce and other
Xsession sessions load it. It is in aptly, and branch `unity/resolute` is
pushed. Build in `~/work/b/nocsd-u2`.

**Issue #1, second reply - measurements done** (2026-09-25, May via the
coordinator): `research/nocsd-reply2/` (holder vs flat on Unity and Plasma,
44-application audit, GTK3, the patch split into four commits with all
combinations building, two gtk-nocsd findings re-checked). Split branch
`split-parts` in `~/work/b/nocsd-up/split` (local). Report sent to the
coordinator. target2 rolled back to Clean-2 (checked inside).

**Trial rebuild of never-built section-B sources** (2026-09-25): 7 of 9 build;
libindicator FTBFS fixed as `+unity1` (built, not in aptly - equivalent to the
archive's binary), vala-panel FTBFS left alone (not used by Unity).
`research/rebuild-trial/`; `packages/libindicator` branch `unity/resolute`
(git-ubuntu clone, no remote of ours); builds in `~/work/b/rebuild`.

**gtk-nocsd global menu, upstream-ready patch** (2026-09-25, May asked):
one commit on upstream main 6b1f70a, desktop-neutral (gtk-shell-shows-menubar),
upstream style; measured on target2, not sent, not in aptly; point 1 (talk
to the maintainer) waits for May. `research/nocsd-upstream/`; branches
`global-menu` in `~/work/b/nocsd-up/src`, `b/global-menu-up` in
`~/work/b/nocsd-merge/pkg` (local only). Tested in real Xfce 4.20 and Plasma 6.6.4
X11 sessions too (`research/nocsd-desktops/`): works on both once
`gtk-shell-shows-menubar` is set, which neither desktop does by itself.
Earlier round (4.8-based): `research/nocsd-merge/`.

**Re-check per host 02:58Z** (2026-09-25): none of B's fixes is in a newer
release (26.10, Debian, upstream) - all patches stay; DECISIONS 2026-09-25.
Found: indicator-keyboard 0ubuntu4 in 26.10 lost its user unit too (not
reported).

**unity-gtk4-menu 0.9** (2026-09-25): issue #1 - 0.8 recursed to SIGSEGV next
to gtk-nocsd built by upstream `make`; 0.9 uses glibc's `dlsym@GLIBC_2.34`.
In aptly, on target2, checked in the live Unity session (C, gjs, Python,
class actions); `research/nocsd-order/`. Issue #1 not answered (May).
Build in `~/work/b/out09`; gtk-nocsd head in `~/work/b/nocsd-head/`.

**indicator-keyboard +unity2** (2026-09-25): test mock fixed (LP #1968333,
Vala notify emission), tests fatal again, 9/9; in aptly, target2 runs it.
Build in `~/work/b/kbt`.

**indicator-datetime/power/session/sound/keyboard +unity1** (2026-09-25):
FTBFS fixes, branches `unity/resolute`, in aptly; `research/indicator-ftbfs/`.
target2 runs them. Builds in `~/work/b/indf`.

**appmenu-gtk-module 25.04-1build1+unity1** (2026-09-25): upstream a783b01c,
in aptly; `research/appmenu-resident/`. target2 has it (dpkg -i) and
`xsettingsd` installed for the reproduction.

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
Released 0.4-0.9, all in aptly. Open: the architecture question vs gtk-nocsd
(DECISIONS 2026-09-25) waits for May.

Qt global menu: measured, already works (Qt5, Qt6, KDE) - nothing to build.

Proposed next, none started - May decides: whether to report the two
gtk-nocsd findings and nux's broken ICU conversions upstream (on hold).

## State of `target2`

**Rolled back to `Clean-2` on 2026-09-25 13:20Z** (host, after the Xfce/KDE
test; checked inside: fresh boot, no `~/.dirty`, archive gtk-nocsd
`3+0~20260321+0b77e1b-1`, no Xfce/Plasma). Everything B had installed there
before is gone: our aptly packages, test applications, `~/b/` scripts. The
scripts that matter are in git (`research/nocsd-order/`,
`research/nocsd-desktops/`, `research/layer-b/`); `~/b/classtest` has to be
rebuilt from `packages/unity-gtk4-menu/tests/classtest.c` before reuse.
No aptly source configured on it.

## Mine outside git

- `/var/tmp/sbuild-claude/b-dev` - now also has libadwaita-1-dev (2026-09-25), Qt6 dev, Xvfb, xfwm4,
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
