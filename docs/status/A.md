# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now

Nothing in flight. Last (2026-09-26): A-5 unity-greeter `+unity1` rebuildable again, in aptly (`research/unity-greeter-rebuild/`). Before: A-4 cinnamon-session #202 - not reachable in our session, nothing to
change (`research/cinnamon-session-214-202/`); A-3 xorg-server
`1.3+unity2`; A-2 no change needed; A-1 six known issues re-checked from a
clean snapshot (`research/recheck-2026-09-26/`). target = aptly (restored from
`Clean-updated-2026-09-23`, our aptly added, full-upgrade), plus test tools
(xdotool, gdb, x11-utils, gnome-text-editor, gnome-characters) and the test
scripts in `~`. The `xorg-watch` systemd user timer on builder stays enabled
(monitoring, not a test).

## State of `target`

Since 2026-09-24 13:11 boot (full upgrade from our aptly), plus by `dpkg -i`
then matched by aptly: unity `+unity10` (2026-09-26), compiz `+unity2`, gtk-nocsd `4.8-1+unity1`
(dbgsyms for them installed too); xorg-server `2:21.1.22-1ubuntu1.3+unity1` (matched by aptly); unity-settings-daemon `0ubuntu7+unity4` (dpkg -i, matched by aptly; dbgsym removed, test divert removed); `~/evinject.py`, `~/evabs.py`, `~/steal-idle.py`, `~/repro1.sh`, `~/cursor-loop.sh` and results in `~/cur/`, rebooted 2026-09-25 ~20:30Z; see `research/xorg-versioning/`. Workspaces 2x2, six terminals spread over
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
- (`packages/gtk-nocsd` handed to agent B, 2026-09-26.)
- `packages/unity-settings-daemon` - branch `unity/resolute` (`0ubuntu7+unity4`, worktree `~/work/a/usd`, based on the unreleased git head 216f054), https://github.com/Ubuntu-Unity-LifeSupport/unity-settings-daemon.
- `packages/unity-greeter` - branch `unity/resolute` (`25.04.1-0ubuntu1+unity1`, native), https://github.com/Ubuntu-Unity-LifeSupport/unity-greeter.
