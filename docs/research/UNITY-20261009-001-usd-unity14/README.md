# UNITY-20261009-001: unity-settings-daemon +unity14 (automount helper)

Agent A, target `target-desktop`.

## What is fixed

| package | version | change |
|---|---|---|
| unity-settings-daemon | 15.04.1+21.10.20220802-0ubuntu7+unity14 | Commits on the published +unity13 (`5a0a300`), in `plugins/automount/`. |

The automount helper no longer shows or keeps its mount prompts and dialogs
while the session is locked or inactive. The rule is the one it already
uses for mounting and autorun: the session is active and known to be
unlocked.

- `5f146c2`: the change, with a new internal module
  `plugins/automount/gsd-mount-guard.[ch]` used by the helper only.
- `2b2999c`, `daaa75a`, `a164d0b`, `4541793`, `dd209ec`: tests
  (`test-mount-guard`, `test-automount`, `test-autorun`), run by
  `make check`.
- `44f5ec2`: changelog.

There is no library or ABI change.

## Build

Built with `scripts/build_sbuild.py` from the package branch
`a/UNITY-20261009-001` (`dd209ec`), chroot snapshot T=20261008T083223Z.
`make check`: test-mount-guard, test-automount, test-autorun and
gcm-self-test PASS. The manifest is in `build/`.

## Checks

- **Tests:** the new cases fail on +unity13 and pass on +unity14; the
  older cases pass on both.
- **Target** (`gate/target-test.txt`), published configuration plus
  +unity14:
  - a medium inserted into the unlocked session is mounted;
  - with autorun enabled by the user, the autorun dialog appears as
    before, and its Eject button works;
  - the dialog closes when the medium is unmounted, and when the session
    locks.

## Verification

- Target test before publication: PASS (`gate/target-test.txt`).
- Check on the target after publication: PASS. Published 2026-10-12
  22:58:56Z as `unity-resolute-20261009-001`; the target updated from the
  live repository, cold boot: the helper runs the published binary, an
  inserted medium is mounted (`gate/target-verification.txt`).
- Independent verification: PASS (the Verifier reviewed the diff against the
  approved design, the tests and their run on +unity13, the build record and
  the target record; it did not reproduce on its own).

## Not changed / known limits

- Mount prompts on the target (a medium that asks for a password, a busy
  unmount) were not produced on the target; they are covered by the test
  suite.

## Publication

- **Database backup:** `/home/claude/backups/UNITY-20261009-001-20261012T225412Z`.
  19 files, complete, equal to live; list sha256
  `c72069f9f78ac694fc6828e64b7f46ee83c90d242388d4ac3f164d3ec8024e12`.
- **Repository:** 8 records added to `unity-resolute` (the source, 5 .deb
  and 2 .ddeb). The sha256 of every pool file matches the build manifest.
- **Snapshot:** `unity-resolute-20261009-001`, which is the live
  `unity-resolute-20261010-001` plus these 8 records
  (`gate/snapshot-diff.txt`).
- **Version safety:** SAFE (`gate/version-check.json`,
  `gate/version-safety.json`).
- **Peer notice:** agent B, ACK.
