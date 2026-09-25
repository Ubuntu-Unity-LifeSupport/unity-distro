# Trial rebuild of section B's never-built sources in resolute

Agent B, 2026-09-25. `docs/STACK-HEALTH.md` section B named several sources
nobody had built in 26.04 - "nobody would know it no longer compiles until
someone rebuilds it". The indicators taught us that this is real (five of
them turned out FTBFS). Each was built from the resolute source with
`sbuild -d resolute` (archive only, not our aptly), `run.sh`, results in
`results.txt`. Nothing was published.

| Source | resolute version | Result |
|---|---|---|
| libunity | 7.1.4+19.04.20190319-6.1ubuntu1 | builds (489 s) |
| unity-lens-applications | 7.1.0+16.10.20160927-0ubuntu8 | builds |
| unity-lens-files | 7.1.0+17.10.20170605-0ubuntu6 | builds |
| unity-scope-home | 6.8.2+19.04.20190412-0ubuntu8 | builds |
| indicator-application | 12.10.1+19.04.20190308.1-0ubuntu6 | builds |
| indicator-appmenu | 15.02.0+20.10.20260311-0ubuntu1 | builds |
| indicator-notifications | 0.4.2-0ubuntu5 | builds |
| **libindicator** | 16.10.0+18.04.20180321.1-0ubuntu8 | **FTBFS** - fixed as `+unity1` |
| **vala-panel** | 24.05-3 | **FTBFS** - not ours to fix, see below |

## libindicator - the one that matters

`dh_install --fail-missing` stops: `indicator-common missing files:
usr/lib/systemd`. The same cause as indicator-bluetooth/-printers
(`research/indicator-units/`): `configure.ac` asks `systemd.pc` for
`systemduserunitdir`, `systemd.pc` moved to `systemd-dev`, and libindicator's
Build-Depends never named systemd at all - it used to arrive indirectly. The
archive's binaries predate the move (last upload: a no-change rebuild for
noble, CVE-2024-3094), so nothing is broken on a running system today.

Why it matters: the missing file is `indicators-pre.target`, and
`unity-panel-service.service` has `BindsTo=indicators-pre.target`
(`packages/unity/services/unity-panel-service.service.in:5`). All seven
indicator services order themselves `After=` it. A rebuild that silenced the
error would ship a libindicator without the target, and Unity's panel service
would not start. Any rebuild at all - a security fix, a transition, a change
of ours - hits this first.

Rule 0: resolute and 26.10 (stonking) both have 0ubuntu8; Debian has no
libindicator; upstream (lp:libindicator) dead since 2018. Nothing to take.

Fix: `systemd-dev` added to Build-Depends (`packages/libindicator`, git-ubuntu
clone, branch `unity/resolute`, `f75a617`), version
`16.10.0+18.04.20180321.1-0ubuntu8+unity1`. Built in sbuild: successful; the
six binaries have the same file lists as the archive's (changelog aside),
`indicators-pre.target` included; `libindicator3.so.7` exports the same 84
symbols. The package's build runs no tests. **Built, not in aptly**: the
binary is equivalent to the archive's, so it goes in with the first real
change to libindicator, or when May wants it there.

## vala-panel - known, not ours

`launchbar-button.vala:143/146: The name 'launch' does not exist in the
context of 'ValaPanel'`. Debian serious bug
[#1118323](https://bugs.debian.org/1118323) (2025-10-17, no patch, no reply;
removed from testing). Cause (from upstream's fix): GLib moved
`GDesktopAppInfo` to the `GioUnix-2.0` GIR namespace, the generated GIR does
not include it, and vapigen silently drops `vala_panel_launch` from the
vapi. Fixed on upstream master in
[5e821ba2](https://gitlab.com/vala-panel-project/vala-panel/-/commit/5e821ba251972e96c161e1a4fc9a927aabc4101d)
and
[82005703](https://gitlab.com/vala-panel-project/vala-panel/-/commit/820057031abfb8cdfe8a38424c6cdeb01f023ea5)
(2025-12-03), in no release (latest tag 24.05); 26.10 and Debian both still
24.05-3.

Unity does not use it: `libvalapanel0` is needed by the vala-panel panel and
by vala-panel-appmenu's Xfce/MATE/Budgie plugins, not by
appmenu-gtk-module or anything in our session. Not patched; if it is ever
needed, the two commits apply to 24.05.
