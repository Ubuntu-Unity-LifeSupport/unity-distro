# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now (2026-09-29 18:55Z)

**UNITY-20260927-040** (unity: Edge::ButtonDownEvent releases compiz's grab
during expo; A2 = any-grab guard) - PUBLISHED 2026-09-29 18:40:26Z (snapshot
`unity-resolute-20260927-040`), target verified from the repository; DONE
after the coordinator merges branch `a/UNITY-20260927-040` (`fa7ea4c`).
Card: `docs/research/UNITY-20260927-040-edge-grab-guard/` (README.md,
target-verification.md). Follow-ups UNITY-20260929-010, -011, -012.

**UNITY-20260929-014** (build_dependencies hardening from -013's Verifier
round 2) - REVIEW, Verifier PASS (INDEPENDENTLY_REPRODUCED); branch
`a/UNITY-20260929-014` (`859e0cd`, worktree `~/work/a/unity-distro-014`)
for the coordinator to merge; DONE after the merge.

Done today: UNITY-20260928-019 (lightdm +unity2, published),
UNITY-20260929-013 (`build_sbuild.py --extra-package`, merged),
UNITY-20260927-047 phase L captures.

My other open tasks are unchanged: UNITY-20260928-022 (its handoff is on
branch `a/UNITY-20260928-022`, not in main - the coordinator handles that),
UNITY-20260927-012, UNITY-20260927-052, UNITY-20260928-008.

## State of `target`

2026-09-29 18:49Z (UNITY-20260927-040): published unity `+unity12` and
lightdm `+unity2` from our repository, workspaces 1x1, test tools and
results removed, rebooted; the two UNITY-20260927-047 capture files stay in
`~`; `~/.dirty` present. A VBoxSVC restart for the wedged oem-test was
pending (the coordinator's and May's decision); check target from inside
the guest after it. Earlier states below are history:

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
