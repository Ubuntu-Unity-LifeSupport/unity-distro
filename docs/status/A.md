# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now (2026-09-29, UNITY-20260928-019)

**UNITY-20260928-019** (lightdm: the greeter's session cleanup is cut short
by the second SIGTERM) - BLOCKED at the publication gate (aptly freeze #1),
resume_state REVIEW. Verifier round 2 PASS (REVIEWED; round 1 FAIL
TEST_INVALID on the tests, fixed with no code change); Design Challenger
APPROVE (round 2). Card:
`docs/research/UNITY-20260928-019-lightdm-greeter-pam-close/README.md`.
Candidate lightdm `1.32.0-6ubuntu4+unity2` =
Ubuntu-Unity-LifeSupport/lightdm branch `a/UNITY-20260928-019` at `f5af23c`
(patch `db13faf` = `d/p/0010-...`, on `unity/resolute` `50a6a5d`). Debs and
full build log in `~/work/a/019-build/out/` (manifest and xz log committed
under `build-unity2/`); package checkout `~/work/a/019-lightdm`. Evidence:
`~/coordinator/evidence/UNITY-20260928-019.json`. Still to do when the freeze
lifts: full `apt_view.py` + `version_safety.py` against the gated snapshot,
release gate, publication, check on target. DECISIONS/PATCHES entries in
main (`eef5c1e`, via `append_record.py`).

Follow-ups proposed to C (no IDs yet): arm the alarm after `waitpid()` also
when a SIGTERM was passed on before reaping (that path keeps today's 90 s
bound); cinnamon-session refusing `Logout` (`NotInRunning`) or hanging in it
on an unresponsive at-spi-registryd inhibitor, seen in the test cycles.

My other open tasks are unchanged: UNITY-20260928-022 (its handoff is on
branch `a/UNITY-20260928-022`, not in main - the coordinator handles that),
UNITY-20260927-012, UNITY-20260927-052, UNITY-20260928-008.

## State of `target`

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
