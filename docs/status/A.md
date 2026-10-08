# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now (2026-10-03 00:35Z) - STOPPED by May (via C); nothing in progress

All agents stopped. Slot A for u-s-d +unity11 was revoked before any
repository step (no db backup, no repo add, no snapshot). Nothing pushed
since the stop.

**UNITY-20261002-003** (u-s-d power: idle watches end in stop()) with
**UNITY-20261002-011** (AC sleep override, moved into u-s-d by C):
- u-s-d +unity11, package branch `a/UNITY-20261002-003` (`89648a3`) on
  GitHub; gated build PASS; -011's own build byte-identical.
- Verifier PASS (REVIEWED); target tests and regressions done.
- Where it stopped: C's condition 2 (one natural boot in the users'
  environment) is DONE and recorded; the next step would have been the slot
  (db backup, repo add, snapshot from live -002, gate).
- Meta records in a local-only branch `a/UNITY-20261002-003` (`8c5b2b1`,
  worktree `~/work/a/unity-distro-003`), NOT pushed (C: do not push).

**UNITY-20260927-053** (automount / SessionIsActive) and **UNITY-20261002-012**
(SECURITY) / **-013**: on hold. Details are private by C's decision; the
meta branch `a/UNITY-20260927-053` (`c01ade9`) is local only (removed from
GitHub by C on May's decision) - do not push it. cinnamon-session +unity4
(package branch `a/UNITY-20260927-053`) is built and must not be published.

## State of `target`

2026-10-03 00:35Z: restored to `Clean-updated-2026-09-23` on 2026-10-02 and
upgraded from our repository (published stack); then u-s-d +unity11 from the
gated build (dpkg, with dbgsym). cinnamon-session is the published
6.4.2-1+unity3 again (the test build +unity4 was removed); GRUB without
`gnome.is_vm=0` (restored 00:23:45Z, `/proc/cmdline` checked);
`apps.light-locker lock-after-screensaver` back to 5; valgrind not
installed; test scripts and debs in `~`; `~/.dirty` present. Earlier states
below are history:

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
