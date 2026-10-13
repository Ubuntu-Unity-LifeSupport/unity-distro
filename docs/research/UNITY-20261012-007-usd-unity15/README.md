# UNITY-20261012-007, UNITY-20261012-008, UNITY-20261012-009: unity-settings-daemon +unity15 (automount helper)

Agent A, target `target-desktop`.

## What is fixed

| package | version | change |
|---|---|---|
| unity-settings-daemon | 15.04.1+21.10.20220802-0ubuntu7+unity15 | Commits on the published +unity14 (`dd209ec`), branch `a/UNITY-20261012-007`, in `plugins/automount/`. |

Follow-ups of +unity14 (UNITY-20261009-001):

- `d19d7cd` (-007): hardening in the mount guard's cleanup when the
  helper stops.
- `d197530` (-007): a test of that cleanup (`test-mount-guard`, built
  with AddressSanitizer in `make check`).
- `3a5030b` (-008): tests of the helper: its dialogs close when the
  session locks or becomes inactive, `stop()` withdraws a pending prompt
  and closes the dialogs, and a prompt is withdrawn when a screen locker
  appears on the bus.
- `4e812af` (-009): `test-autorun` shows GTK's real question dialog for an
  unmount and checks that it closes; the comment on the old stand-in is
  gone with it.
- `2d0e9bf`: changelog. No change to `debian/control`.

There is no library or ABI change, and no change in behaviour the user can
see.

## Build

Built with `scripts/build_sbuild.py` from the package branch
`a/UNITY-20261012-007` (`2d0e9bf`), chroot snapshot T=20261008T083223Z.
`make check`: test-mount-guard, test-automount, test-autorun and
gcm-self-test PASS; test-mount-guard is compiled and linked with
`-fsanitize=address`. The manifest is in `build/`.

## Checks

- **Tests:** on +unity14 with the new tests, the new test-mount-guard case
  fails; the other new cases pass on both (they cover existing behaviour).
  On +unity15 all pass.
- **Target** (`gate/target-test.txt`), live stack plus +unity15: a medium
  inserted into the unlocked session is mounted; with autorun enabled the
  autorun dialog appears and its Eject button works; the dialog closes when
  the medium is unmounted and when the session locks; after a power-off with
  the medium mounted, no crash report.

## Verification

- Target test before publication: PASS (`gate/target-test.txt`).
- Check on the target after publication: PASS. Published 2026-10-13
  10:17:23Z as `unity-resolute-20261012-007`; the target restored and
  updated from the live repository, cold boot: the helper runs the
  published binary, an inserted medium is mounted
  (`gate/target-verification.txt`).
- Independent verification: PASS (the Verifier reviewed the diff against the
  approved design, the tests on +unity14 and +unity15 and ran the new
  test-mount-guard case itself, the build record, and the target record
  against its raw files).

## Not changed / known limits

- Mount prompts (a medium that asks for a password, a busy unmount) and
  the changed cleanup are not produced on the target; they are covered by
  the test suite.

## Publication

- **Database backup:** `/home/claude/backups/UNITY-20261012-007-20261013T100904Z`.
  20 files, complete, equal to live; list sha256
  `3dfae61eee407223c3318a6f26851addda8fe9576b828056d37109f272c10465`.
- **Repository:** 8 records added to `unity-resolute` (the source, 5 .deb
  and 2 .ddeb). The sha256 of every pool file matches the build manifest.
- **Snapshot:** `unity-resolute-20261012-007`, which is the live
  `unity-resolute-20261013-003` plus these 8 records
  (`gate/snapshot-diff.txt`).
- **Version safety:** SAFE (`gate/version-check.json`,
  `gate/version-safety.json`).
- **Peer notice:** agent B, ACK.
