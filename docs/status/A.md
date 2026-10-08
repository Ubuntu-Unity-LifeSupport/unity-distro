# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now (2026-10-08 06:30Z) - waiting for vbox

Done today:
- **UNITY-20261002-003** (u-s-d power: idle watches end in stop()) and
  **UNITY-20261002-011** (no suspend on AC: override in the schemas package):
  u-s-d +unity11 published 2026-10-08 03:05Z (snapshot
  `unity-resolute-20261002-003-r2`), target verified over ssh, merged by the
  coordinator, DONE.
- Tool and docs tasks while vbox is down, each merged by the coordinator
  and DONE:
  - **UNITY-20261002-001**: the `test_tested_with` fixture no longer
    collides within one second.
  - **UNITY-20260929-009**: section 6 publication sequence with
    `[tool]`/`[process]` rules.
  - **UNITY-20261008-002**: the publisher checks every binary's sha256 in
    the gated snapshot.
  - **UNITY-20261008-003**: `published_by` compares bytes or buildinfo
    identity, and the gate and publisher require a committed `.buildinfo`.
  - **UNITY-20261008-004**: canonical `scripts/backup_aptly_db.py`. Its one
    live run left the backup
    `~/backups/UNITY-20261008-004-20261008T050534Z`, kept as a rollback
    point.
  - **UNITY-20261008-005**: the apt view identifies the snapshot by
    content (`content_sha256`).

Next, by C's plan: **UNITY-20261002-012** (SECURITY, details private), only
once the vbox MCP server is back (its tests need snapshots and rollbacks).
On hold with it: UNITY-20260927-053 (cinnamon-session +unity4 built, not to
be published) and UNITY-20261002-013. The meta branch
`a/UNITY-20260927-053` stays local - do not push it.

## State of `target`

2026-10-08 03:15Z: published stack from our repository, including u-s-d
+unity11 (the three debs taken from the repository with apt-get download,
equal to the published ones), with the two dbgsym packages of the tested
build; cinnamon-session 6.4.2-1+unity3; no `gnome.is_vm`; test scripts and
debs in `~`; `~/.dirty` present. vbox MCP unavailable (checks over ssh).
Earlier states below are history:

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
