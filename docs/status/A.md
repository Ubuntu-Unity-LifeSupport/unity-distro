# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now

Nothing in flight. Last (2026-09-25, new A session `Агент A`): rule 0 release
re-check of all A's fixes - no newer release contains any of them, patch stays
everywhere (DECISIONS 2026-09-25, `research/release-recheck-a/`). Measurement
builds in `~/work/a/relcheck/` (cinnamon-session 6.6.4 relaxed, u-s-d
26.10.1ubuntu, xorg-server 21.1.24, lightdm 1.33.1 - all build in resolute;
nothing published). xorg-server `2:21.1.22-1ubuntu1.3+unity1` (11 CVEs, Ubuntu base so its updates win) in aptly;
`xorg-watch.timer` (systemd user, builder) flags new resolute uploads - `research/xorg-versioning/`. For May: the CLAUDE.md cinnamon-session example (the 6.6 bound is packaging only).
Open: #3 itself (not reproduced).

## State of `target`

Since 2026-09-24 13:11 boot (full upgrade from our aptly), plus by `dpkg -i`
then matched by aptly: unity `+unity9`, compiz `+unity2`, gtk-nocsd `4.8-1+unity1`
(dbgsyms for them installed too); xorg-server `2:21.1.22-1ubuntu1.3+unity1` (dpkg -i, matched by aptly since 2026-09-25 21:00Z), rebooted 2026-09-25 ~20:30Z; see `research/xorg-versioning/`. Workspaces 2x2, six terminals spread over
them. Also installed: libxpathselect1.4v5 (Unity introspection),
libunity-gtk4-menu0 0.8, gnome-characters, gnome-text-editor,
gnome-sound-recorder, google-chrome-stable 154 (adds `google-chrome.sources`); xdotool, gdb,
test scripts in `~`; unity-session `49.4+unity1`. Clock was 1 h 07 min behind, set from builder at 17:26Z
- not synchronised, check after a host sleep. `~/.dirty` present.

## Mine in `packages/`

- `packages/unity` - branches `unity/resolute` (released `+unity9`),
  `mr/stale-pending-action` (worktree `/var/tmp/sbuild-claude/unity-mr`),
  `exp/option-b-request-shutdown` (rejected experiment).
- `packages/cinnamon-session` - gbp repository, branch `unity/resolute`
  (`6.4.2-1+unity3`), https://github.com/Ubuntu-Unity-LifeSupport/cinnamon-session.
- `packages/unity` branch `wip/confirm-inhibitors` (worktree `~/work/a/unity`),
  `+unity3` (not published) and `+unity4`.
- `packages/compiz` - branch `unity/resolute` (`+unity2`), https://github.com/Ubuntu-Unity-LifeSupport/compiz.
- `packages/unity` - `unity/resolute` at `+unity8` (tag), built from worktree
  `~/work/a/unity` branch `fix/compiz-teardown` (merged).
- `packages/lightdm` - gbp, branch `unity/resolute` (`1.32.0-6ubuntu4+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/lightdm.
- `packages/unity-session` - branch `unity/resolute` (`49.4+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/unity-session.
- `packages/gtk-nocsd` - salsa packaging, branch `unity/resolute` (`4.8-1+unity1`,
  merge of Debian 4.8-1, no patches), https://github.com/Ubuntu-Unity-LifeSupport/gtk-nocsd.
- `packages/unity-settings-daemon` - branch `unity/resolute` (`0ubuntu7+unity3`, based on the unreleased git head 216f054).
