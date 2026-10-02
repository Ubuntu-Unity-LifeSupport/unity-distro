# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now (2026-10-02 19:35Z) - no tasks (May, via C)

All u-s-d tasks of 2026-10-02 are DONE:
- UNITY-20260927-012 + UNITY-20260927-052: u-s-d +unity7 published 15:15Z
  (snapshot `unity-resolute-20260927-012`), verified on target;
- UNITY-20260928-022: u-s-d +unity9 published ~15:40Z
  (`unity-resolute-20260928-022`), verified with the pre-existing Power
  registration race as a limitation;
- UNITY-20261002-002: u-s-d +unity10 published 19:13Z
  (`unity-resolute-20261002-002`), the fix for that race (the D-Bus
  registration lives with the manager object); DC APPROVE, Verifier PASS
  (INDEPENDENTLY_REPRODUCED), target verified through the repository with
  two natural boots; branch merged by the coordinator (main 0420698).

Records: cards under `docs/research/UNITY-20260927-012-...`,
`UNITY-20260928-022-...`, `UNITY-20261002-002-...`; PATCHES sections for
+unity7, +unity9, +unity10 (with corrections); DECISIONS of 2026-10-02
(+unity7 as one version; the known-gap lesson; the -002 lifetime decision);
UNITY-20261002-009 card with the leads for the trigger.

Follow-ups on the board, unassigned: UNITY-20261002-006 (housekeeping, the
identical gap), -007 (xrandr), -008 (media-keys), -009 (what stops the
power plugin at a session start).

Worktrees: `~/work/a/unity-distro-012`, `-052`, `-002` and
`~/work/a/unity-distro` (-022), all merged; package clones under their
`packages/unity-settings-daemon` (GitHub origin).

## State of `target`

2026-10-02 19:30Z: u-s-d +unity10 from the repository (apt), with the two
dbgsym packages of the gated build (dpkg); unity +unity12, lightdm +unity2
as before; valgrind installed (for the -052 regression); test scripts of
-012/-052/-022/-002 in `~` (and `~/u7g`, `~/u9g`, `~/u10` with the debs);
no drop-ins, no test units, no tracer; `~/.dirty` present. B's hud,
libindicator and indicator-datetime publications of today are NOT installed
there (no apt upgrade run). Earlier states below are history:

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
