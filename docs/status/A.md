# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now

**#6 done locally (2026-09-24).** unity `+unity4`, cinnamon-session
`+unity1`, compiz `+unity1` published to aptly with May's approval and
verified from a clean snapshot through apt: one dialog on every path,
inhibitors shown, no compiz exit crash in five restarts. Upstream drafts not
written yet (Unity MR, compiz, Linux Mint feature request). Next: May's call.

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
