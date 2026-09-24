# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now

Layer A list done as far as it goes (DECISIONS 2026-09-24, "agent A's Layer A
list"). Open: #3 (not reproduced, tools ready), the workspace side bug of the
#3 workaround (not tested). Waiting for May's next direction.

## State of `target`

Rolled back to `Clean-updated-2026-09-23` at 2026-09-24 06:38Z, then dirtied
(`~/.dirty`): our apt source, the trio from aptly, xdotool, `~/t.sh`,
`~/coreprep.sh`, run logs under `~/opt/`. Kernel `core_pattern` is set per
boot by `coreprep.sh` only.

## Mine in `packages/`

- `packages/unity` - branches `unity/resolute` (released `+unity2`),
  `mr/stale-pending-action` (worktree `/var/tmp/sbuild-claude/unity-mr`),
  `exp/option-b-request-shutdown` (rejected experiment).
- `packages/cinnamon-session` - gbp repository, branch `unity/resolute`
  (`6.4.2-1+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/cinnamon-session.
- `packages/unity` branch `wip/confirm-inhibitors` (worktree `~/work/a/unity`),
  `+unity3` (not published) and `+unity4`.
- `packages/compiz` - branch `unity/resolute` (`+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/compiz.
