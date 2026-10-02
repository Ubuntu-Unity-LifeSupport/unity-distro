# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now (2026-10-02 19:05Z) - UNITY-20261002-002 at the publication gate

**UNITY-20261002-002** (u-s-d power: D-Bus registration lost when stop()
runs before the bus result; fix forward as +unity10, May's decision via C)
- IMPLEMENTING -> gate: branch `a/UNITY-20261002-002` (worktree
  `~/work/a/unity-distro-002`); package
  `Ubuntu-Unity-LifeSupport/unity-settings-daemon` branch
  `a/UNITY-20261002-002` at `122c413` (fix `ca997f7` on +unity9 `57945f5`).
- Gated build on chroot 20260929T201245Z (`build/`), the same debs tested on
  target (`tested_build: this_build`).
- Design Challenger APPROVE; Verifier PASS (INDEPENDENTLY_REPRODUCED), 7
  non-blocking remarks handled in the card; one left to C: the changelog
  says "4-6 s" for the window, measured 4-11 s / up to 28.6 s.
- Tests: gdb stop-before-bus FAIL on +unity9/+unity7, PASS on +unity10; key
  toggle inside the window PASS on both (dispatch order - a demonstration
  limit, accepted by C); valgrind race 0 errors; -022/-012/-052 regressions;
  natural boots 19 (+unity9) + 10 (+unity10), no stop, Power owned.
- Waiting for "slot A" (B publishes hud, libindicator, indicator-datetime
  first); then db backup, repo add, snapshot, gate, May's confirmation.
- Follow-ups on the board: -006 housekeeping (same gap), -007 xrandr,
  -008 media-keys, -009 the trigger at session start (card with leads).

Done today (2026-10-02):
- UNITY-20260927-012 + UNITY-20260927-052: u-s-d +unity7 published
  15:15Z, verified, DONE;
- UNITY-20260928-022: u-s-d +unity9 published ~15:40Z, verified with the
  pre-existing Power registration race as a limitation, DONE;
- lesson recorded in DECISIONS: a known gap in the changed code path needs a
  board task or a measurement before the gate; publication checks without
  test drop-ins.

## State of `target`

2026-10-02 ~19:00Z: u-s-d +unity10 (tested build, with dbgsym) installed by
dpkg over the published +unity9; rebooted after the test units
(`u002-trace.service`, `u002-window-toggle.service`) were removed; no
drop-ins; valgrind and the test scripts of -012/-052/-022/-002 in `~`;
`~/.dirty` present. Earlier states below are history:

Restored again 2026-09-29 11:04Z (UNITY-20260927-040) from
`Clean-updated-2026-09-23` (fresh boot, no `~/.dirty`), our repository added,
`full-upgrade`; xdotool, x11-utils, xterm, python3-evdev installed. After the
tests: unity back to the published `+unity11`, workspaces 1x1 again, test
files removed, rebooted; the two 047 capture files stay in `~`. `~/.dirty`
present. The earlier restore of the same day (below) is superseded:

Restored 2026-09-29 07:55Z from `Clean-updated-2026-09-23` (confirmed from
the guest: fresh boot, no `~/.dirty`), then: our aptly added
(`/etc/apt/sources.list.d/unity-distro.list`, key
`/usr/share/keyrings/unity-distro.gpg`), `full-upgrade` to our stack;
xdotool, xauth, x11-utils installed. lightdm back to aptly `+unity1` after
the +unity2 tests; the test user `utest`, the pam_exec test hook and the test
scripts removed. `~/.dirty` present. Everything older in this file's history
(the pre-2026-09-29 target state) no longer applies - the snapshot restore
discarded it.

## Mine in `packages/`

- `packages/unity` - branches `unity/resolute` (released `+unity9`),
  `mr/stale-pending-action` (worktree `/var/tmp/sbuild-claude/unity-mr`),
  `exp/option-b-request-shutdown` (rejected experiment).
- `packages/cinnamon-session` - gbp repository, branch `unity/resolute`
  (`6.4.2-1+unity3`), https://github.com/Ubuntu-Unity-LifeSupport/cinnamon-session.
- `packages/unity` - task branch `a/UNITY-20260927-040` (`+unity12`, not in our repository yet; checkout `~/work/a/040-unity`).
- `packages/unity` branch `wip/confirm-inhibitors` (worktree `~/work/a/unity`),
  `+unity3` (not published) and `+unity4`.
- `packages/compiz` - branch `unity/resolute` (`+unity2`), https://github.com/Ubuntu-Unity-LifeSupport/compiz.
- `packages/unity` - `unity/resolute` at `+unity8` (tag), built from worktree
  `~/work/a/unity` branch `fix/compiz-teardown` (merged).
- `packages/lightdm` - gbp, branch `unity/resolute` (`1.32.0-6ubuntu4+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/lightdm; branch `a/UNITY-20260928-019` (`+unity2`, not published; checkout `~/work/a/019-lightdm`).
- `packages/unity-session` - branch `unity/resolute` (`49.4+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/unity-session.
- (`packages/gtk-nocsd` handed to agent B, 2026-09-26.)
- `packages/unity-settings-daemon` - branch `unity/resolute` (`0ubuntu7+unity4`, worktree `~/work/a/usd`, based on the unreleased git head 216f054), https://github.com/Ubuntu-Unity-LifeSupport/unity-settings-daemon.
- `packages/unity-greeter` - branch `unity/resolute` (`25.04.1-0ubuntu1+unity1`, native), https://github.com/Ubuntu-Unity-LifeSupport/unity-greeter.
- `packages/unity-control-center` - branch `unity/resolute` (`0ubuntu13+unity2`), https://github.com/Ubuntu-Unity-LifeSupport/unity-control-center.
- `packages/session-migration` - branch `unity/resolute` (`0.3.9build2+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/session-migration.
