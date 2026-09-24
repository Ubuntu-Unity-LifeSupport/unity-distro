# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now

Layer A list done as far as it goes (DECISIONS 2026-09-24, "agent A's Layer A
list"). Open: #3 (not reproduced, tools ready), the workspace side bug of the
#3 workaround (not tested). Waiting for May's next direction.

## State of `target`

2026-09-24 13:11 boot: `apt full-upgrade` from our aptly on top of the
rolled-back snapshot - every package we publish that is installed there is
ours: unity `+unity5`, compiz `+unity1`, cinnamon-session `+unity2`,
unity-settings-daemon `0ubuntu7+unity1`, nux `0ubuntu15+unity1` (agent B),
light-locker `+unity2`. Smoke test after reboot: light-locker running, no
crash reports at all, Dash search works, power key shows Unity's dialog, no
grab left after Escape. Also installed: xdotool, gdb, `~/t.sh`,
`~/coreprep.sh`, `~/grab-probe`, test scripts; logs under `~/opt/`.

## Mine in `packages/`

- `packages/unity` - branches `unity/resolute` (released `+unity2`),
  `mr/stale-pending-action` (worktree `/var/tmp/sbuild-claude/unity-mr`),
  `exp/option-b-request-shutdown` (rejected experiment).
- `packages/cinnamon-session` - gbp repository, branch `unity/resolute`
  (`6.4.2-1+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/cinnamon-session.
- `packages/unity` branch `wip/confirm-inhibitors` (worktree `~/work/a/unity`),
  `+unity3` (not published) and `+unity4`.
- `packages/compiz` - branch `unity/resolute` (`+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/compiz.
