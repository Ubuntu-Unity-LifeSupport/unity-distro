# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now

Nothing in flight. Last: unity `+unity9` (LP #2160299, #2165662) published
(`research/unity-lp-crashes/`). Open: unity-settings-daemon color plugin
crash at logout (cause found, not fixed); #3 itself (not reproduced).

## State of `target`

Since 2026-09-24 13:11 boot (full upgrade from our aptly), plus by `dpkg -i`
then matched by aptly: unity `+unity9`, compiz `+unity2`, gtk-nocsd `+unity2`
(dbgsyms for them installed too). Workspaces 2x2, six terminals spread over
them. Also installed: libxpathselect1.4v5 (Unity introspection),
libunity-gtk4-menu0 0.8, gnome-characters, gnome-text-editor; xdotool, gdb,
test scripts in `~`; unity-session `49.4+unity1`. Clock was 1 h 07 min behind, set from builder at 17:26Z
- not synchronised, check after a host sleep. `~/.dirty` present.

## Mine in `packages/`

- `packages/unity` - branches `unity/resolute` (released `+unity2`),
  `mr/stale-pending-action` (worktree `/var/tmp/sbuild-claude/unity-mr`),
  `exp/option-b-request-shutdown` (rejected experiment).
- `packages/cinnamon-session` - gbp repository, branch `unity/resolute`
  (`6.4.2-1+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/cinnamon-session.
- `packages/unity` branch `wip/confirm-inhibitors` (worktree `~/work/a/unity`),
  `+unity3` (not published) and `+unity4`.
- `packages/compiz` - branch `unity/resolute` (`+unity2`), https://github.com/Ubuntu-Unity-LifeSupport/compiz.
- `packages/unity` - `unity/resolute` at `+unity8` (tag), built from worktree
  `~/work/a/unity` branch `fix/compiz-teardown` (merged).
- `packages/unity-session` - branch `unity/resolute` (`49.4+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/unity-session.
- `packages/gtk-nocsd` - salsa packaging, branch `unity/resolute` (`+unity2`,
  two quilt backports), https://github.com/Ubuntu-Unity-LifeSupport/gtk-nocsd.
