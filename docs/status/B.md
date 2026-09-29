# Agent B - running state

Test desktop: `target2` (192.168.56.30, VM `target-desktop-2`, snapshot `Clean-2`)
Build directory: `~/work/b`

## Now

**UNITY-20260927-021** (2026-09-29): calamares-settings-ubuntu
1:26.04.12+unity2. Target PASS; PUBLISHED waits for UNITY-20260929-015.
- Published 16:10Z as snapshot `unity-resolute-20260927-021-r2`.
- Target check on `oem-test`:
  - live ISO session with our repository;
  - fresh Calamares OEM install;
  - two cold first boots from the new snapshot `OEM-ready-unity2`.
  In both boots Calamares is on top, and the wallpaper is DESKTOP/BELOW and
  never focused.
- Limit: apt does not fix an OEM system that is already installed.
  basicwallpaper is unpacked from the installer medium's `oemconfig.tar.gz`
  and belongs to no package.
- Record: `research/UNITY-20260927-021-calamares-oem-wallpaper/target-verification.md`,
  branch `b/UNITY-20260927-021` deb301b.
- `oem-test` is powered off. Snapshots `OEM-ready`, `OEM-ready-fixed` and
  `OEM-ready-unity2` are kept.
- Why it waits: taskctl compares the live snapshot by name, and `./resolute`
  has since moved to `unity-resolute-20260928-019`. That snapshot is a
  superset: only 11 lightdm records were added.
- Next: UNITY-20260929-015, taskctl accepting a live snapshot that contains
  every artifact of the publish record.

**hud** (2026-09-26, B-12): hud is B's now.
- `+unity1` builds in resolute: CMake 4, systemd-dev and C++17 fixed, 6/6
  test suites pass.
- File lists and symbols equal the archive's, and the package is in aptly.
- On target2:
  - the HUD finds GTK4 (unity-gtk4-menu) and GTK3 (appmenu) menus;
  - LibreOffice works only intermittently, as with the archive build;
  - hud-service did not crash.
- See `research/hud/`.
- gtk-nocsd +unity3 is in aptly (May approved it through C).
  `51gtk-nocsd` no longer drops `libunity-gtk4-menu.so.0` from the session.
  Checked under Unity (GTK4 panel menu and HUD) and Xfce.
- Automatic mode is stopped after B-12. No new tasks.

**overlay-scrollbar and ubuntu-unity-meta** (2026-09-26, B-11): both are
B's now.
- overlay-scrollbar `+unity1` is a stub: no GTK2 module, and
  `81overlay-scrollbar` is removed on upgrade.
- ubuntu-unity-meta `0.29+unity1` recommends ayatana-indicator-messages.
- Both are in aptly.
- Verified on target2 by a full-upgrade from Clean-2: the session has no
  `GTK2_MODULES`, and Pidgin raises from the envelope.
- `research/messaging-menu/` (B-11 section).
- Next: hud.

**Messaging menu under Unity** (2026-09-26, B-10): Unity's panel now shows
ayatana-indicator-messages.
- libindicator `+unity2` (Ayatana root and item types) and
  ayatana-indicator-messages `+unity1` (link into
  `/usr/share/unity/indicators`) are in aptly.
- Pidgin and Geary show up; sources are clickable.
- `research/messaging-menu/`.
- The meta and overlay-scrollbar follow-up was done in B-11 (above).

**Target2 checks done** (2026-09-26, B-8, after the VBoxSVC restart):
- unity-lens-files `+unity1` checked live and published.
- appmenu `+unity1` checked with GIMP 3, LibreOffice and Chromium (snap).
  With the archive module GIMP segfaults 2 of 2 when the module is
  dropped; with `+unity1` it survives 2 of 2.
- target2 was restored to Clean-2 after B-12 on 2026-09-26 20:56Z, checked
  inside: fresh boot and no `~/.dirty` marker.

**Rebuild file-loss survey** (2026-09-26, coordinator's task B-7):
`research/rebuild-loss/`.
- 21 sources rebuilt: nothing is lost except by the systemd.pc trap, in
  indicator-messages (fixed in 26.10 as 0ubuntu8) and hud.
- libindicator `+unity1` is published: files and symbols equal to the
  archive's.
- session-migration `+unity1` is built, not published.
- hud `+unity1` is WIP: the googletest C++17 layer is left.
- _Correction 2026-09-27 (UNITY-20260927-036):_ session-migration `+unity1` was published by agent A, and
  hud `+unity1` is in aptly since B-12 (`research/hud/`).
- unity-greeter has no owner; overlay-scrollbar is B's since B-11.

**Only-on-builder commits** of B's git-ubuntu clones are exported to
`docs/package-patches-b/`, since `origin` is Launchpad and we do not push
there.

**Unity scopes** (2026-09-26, coordinator's task B-4): seven Python scopes are
`+unity1` in aptly.
- They install together now.
- manpages works on GTK 4 systems (it asks for GTK 3).
- gnote starts Gnote correctly.
- The table of all 17 packages is in `research/unity-scopes/`; build in
  `~/work/b/scopes`.

**libunity +unity1** (2026-09-26, coordinator's task B-3): unity-scopes-runner
now loads scopes with importlib on Python 3.14.
- Checked in the Dash with unity-scope-calculator.
- In aptly.
- `packages/libunity` (git-ubuntu clone, no remote of ours);
  `research/libunity-python314/`; build in `~/work/b/lu1`.

**indicator-datetime +unity2** (2026-09-26, coordinator's task B-2): LP
#1848969 and #2099742. A task with only a due date aborted the service.
- Reproduced; fixed.
- 29 of 29 tests, including a new one.
- In aptly.
- `research/indicator-datetime-tasks/`; build in `~/work/b/idt-fix`.

**indicator-keyboard +unity3** (2026-09-26, coordinator's task B-1): LP #2166139.
It crashed in g_variant_iter_new when AccountsService had no InputSources
cached, for instance after an accounts-daemon restart.
- Reproduced; fixed.
- 10/10 tests, including a new one.
- In aptly.
- `research/indicator-keyboard-2166139/`; build in `~/work/b/ik3`.

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
_Correction 2026-09-27 (UNITY-20260927-036):_ libindicator `+unity1` was published afterwards; aptly holds
`+unity1` and `+unity2` (`research/UNITY-20260927-036-record-corrections/logs/01-facts.txt`).

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
_Correction 2026-09-27 (UNITY-20260927-036):_ that was the state on 2026-09-25; target2 has been
rolled back to Clean-2 since, so it has neither.

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
user `tester` (password omitted from this public status), `oem` removed.
Snapshot `OEM-ready`
(host) is the state before the end user's first boot, `OEM-ready-fixed` the
same with our basicwallpaper; oem-test currently runs `OEM-ready-fixed`'s
first boot. The black screen seen at the OEM-preparation Unity login was
not agent A's gvfs race (its journal, boot -1 on the `OEM-ready` disk: gvfs
started in 1.8 s, never cancelled); it was a slow first start, ~51 s from
autologin to compiz, told to A; the OEM test account and its password are
omitted from this public status. Rotate any test-VM password that appeared in
Git history; deleting it from the current file does not remove old revisions.

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

**Rolled back to `Clean-2` again on 2026-09-28 ~14:55Z**, after
UNITY-20260927-024 (unity-greeter, indicator-keyboard stock/+unity3, a test
user). Checked inside: no `~/.dirty`, no `ik024test`, archive
indicator-keyboard 0ubuntu1, greeter back to `lightdm-greeter`.

Earlier: **rolled back to `Clean-2` on 2026-09-25 13:20Z** (host, after the Xfce/KDE
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
