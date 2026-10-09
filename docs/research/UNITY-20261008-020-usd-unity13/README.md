# UNITY-20261008-020, UNITY-20261008-009, UNITY-20261008-010: unity-settings-daemon +unity13 (automount helper)

Agent A, target `target-desktop`.

## What is fixed

| package | version | change |
|---|---|---|
| unity-settings-daemon | 15.04.1+21.10.20220802-0ubuntu7+unity13 | Three commits on `unity/resolute` +unity12 (`b116af2`), in `plugins/automount/`. |

- **UNITY-20261008-020** (`ffbd313`): the automount helper offers autorun
  for a medium only when the session is active and known to be unlocked,
  the same condition it already uses for mounting (+unity12). The condition
  is checked when the mount appears and again right before autorun opens a
  folder, shows its dialog or starts an application. A medium mounted from
  the queue once the session is unlocked is offered as before.
- **UNITY-20261008-010** (`f5cca67`): one proxy and one source of answers
  per screen locker name. A locker that leaves the bus and comes back no
  longer leaves an extra proxy and signal handler behind, and an answer
  from a previous owner of the name is ignored.
- **UNITY-20261008-009** (`e78f708`): tests. `test-automount` checks the
  lock predicate (every unknown or locked state refuses), the start-up
  gate, the queue drain and the autorun gate; `test-autorun` checks that
  autorun is asked again before it acts. Both run in `make check`.

`gsd-autorun.h` is internal to the helper binary; there is no library or
ABI change.

## Build

Built with `scripts/build_sbuild.py` from the unity-settings-daemon package
branch `a/UNITY-20261008-020` (5a0a300), in chroot snapshot
T=20261008T083223Z. `make check`: test-automount, test-autorun and
gcm-self-test PASS. The manifest is in `build/`.

## Checks

- **Tests:** the autorun cases fail on +unity12 and pass on +unity13; each
  of seven deliberate changes to the lock and autorun conditions (and to
  the queue drain) makes at least one case fail.
- **Target** (`gate/target-test.txt`), published configuration plus
  +unity13:
  - a medium inserted into the unlocked session is mounted;
  - with autorun enabled by the user, the autorun dialog appears for it as
    before;
  - with Unity's lockscreen (a run outside the published configuration), a
    medium inserted while locked is neither mounted nor offered.

## Verification

- Target test before publication: PASS (`gate/target-test.txt`).
- Independent verification: PASS (the Verifier reviewed the diff, the
  tests, the build record and the runtime records; it did not reproduce on
  its own).
- Check on the target after publication: PASS. Published 2026-10-09
  00:38:37Z as `unity-resolute-20261008-020`; the target updated from the
  live repository, cold boot: the helper runs the published binary, an
  inserted medium is mounted (`gate/target-verification.txt`).

## Publication

- **Database backup:** `/home/claude/backups/UNITY-20261008-020-20261009T003518Z`.
  19 files, complete, equal to live; list sha256
  `b4e7f8be7a9ca443f081c59a2f7c3b98190f25fe4f82ba36147906a490bf0c40`.
- **Repository:** 8 records added to `unity-resolute` (the source, 5 .deb
  and 2 .ddeb). The sha256 of every pool file matches the build manifest.
- **Snapshot:** `unity-resolute-20261008-020`, which is the live
  `unity-resolute-20261008-013` plus these 8 records
  (`gate/snapshot-diff.txt`).
- **Version safety:** SAFE (`gate/version-check.json`,
  `gate/version-safety.json`).
- **Peer notice:** agent B, ACK.

## Not changed / known limits

- Autorun after an unlock was not tested on the target (it needs a login at
  the lock screen); the unlocked behaviour is covered by the target run and
  the tests.
- The proxy change (UNITY-20261008-010) is checked by review; it has no
  automated test.
