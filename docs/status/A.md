# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now

**#6, option A chosen by May (2026-09-24).** Working on the Unity half: Unity
confirms its own pending end-session action even when the session manager's
`Open` lists inhibitors, so under option A (and under gnome-session) a
restart from the menu goes past an inhibitor without showing it. Fix in
`UnityCore/GnomeSessionManager.cpp`, then measure it together with
cinnamon-session option A on `target`. See `research/shutdown-path/`.

## State of `target`

Dirty (`~/.dirty`): unity `+unity2` from aptly, archive cinnamon-session,
xdotool, aptly source, `~/t.sh` and run logs under `~/opt/`.

## Mine in `packages/`

- `packages/unity` - branches `unity/resolute` (released `+unity2`),
  `mr/stale-pending-action` (worktree `/var/tmp/sbuild-claude/unity-mr`),
  `exp/option-b-request-shutdown` (rejected experiment).
- cinnamon-session option A experiment: `~/layera/cs-exp/src` (to move into
  a proper package repository once the direction is final).
