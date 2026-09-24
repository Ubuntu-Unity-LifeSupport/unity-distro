# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now

**#6, option A (May's choice, 2026-09-24).** cinnamon-session `+unity1`
(option A) and unity `+unity4` (inhibitor fixes) built and measured on
`target`: one dialog on every path, inhibitors shown. **Blocked** by a compiz
exit race that option A's timing makes frequent (3 crashes in 7 restarts);
compiz with `_exit(0)` in the XSMP die handler (`+exp1`) measured: 0 crashes
in 8 restarts. Nothing published to aptly yet - waiting for May on the trio
(unity `+unity4`, cinnamon-session `+unity1`, compiz with the exit fix). See `research/shutdown-path/`.

## State of `target`

Dirty (`~/.dirty`): unity `+unity2` from aptly, archive cinnamon-session,
xdotool, aptly source, `~/t.sh` and run logs under `~/opt/`.

## Mine in `packages/`

- `packages/unity` - branches `unity/resolute` (released `+unity2`),
  `mr/stale-pending-action` (worktree `/var/tmp/sbuild-claude/unity-mr`),
  `exp/option-b-request-shutdown` (rejected experiment).
- `packages/cinnamon-session` - gbp repository, branch `unity/resolute`
  (`6.4.2-1+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/cinnamon-session.
- `packages/unity` branch `wip/confirm-inhibitors` (worktree `~/work/a/unity`),
  `+unity3` (not published) and `+unity4`.
- compiz experiment: `~/work/a/compiz/src` (`+exp1`, `_exit` in die handler).
