# UNITY-20261002-001: flaky `test_build_sbuild.test_tested_with`

Task kind: tool (test fixture). Owner: A. Parent: UNITY-20260929-020.
Not a product bug: `build_sbuild.py --tested-with` behaves as designed.

## 1. Reproduction

`test_tested_with` builds once on the `setUp` chroot, then checks
`--tested-with` twice: the same chroot is accepted (rc 0), and an "other"
chroot is refused (rc 2, "the tested build used another chroot").

The "other" chroot is `make_chroot(self.base / "other")`, built with the same
defaults as the `setUp` one:
- `stamp = stamp_days_ago(1)`, which has one-second resolution;
- the same `sources.list` (it embeds the stamp), `dpkg/status` and file
  names;
- `tar --zstd -cf ... -C root .`, so the member mtimes are the creation
  second.

When both fixtures are made within the same wall-clock second, the two
tarballs are byte-identical. They have the same sha256, `--tested-with` correctly
accepts the build, and the test fails with `0 != 2`. This was seen on
2026-10-02. In normal runs, the two builds between the fixtures take more
than a second, so the test passes (5/5 on main `9bb61c9`).

Deterministic reproduction, with the fixture clock frozen (one stamp and one
tar mtime): `tools/frozen-test.py` gives
`runs/01-frozen-main.txt`: `AssertionError: 0 != 2`. `tools/repro.py` shows the
two fixtures alone with the same sha256.

## 2. Existing fix

None. The test and fixture are unchanged since UNITY-20260929-020. No other
task names this test (board grep). Result: `NOT_FIXED`; issue search:
`NOT_FOUND` (internal tool).

## 3. Root cause and invariant

Root cause: the "other" fixture differs from the first only by time, at
one-second resolution. Its content is not guaranteed to differ.

Invariant: a fixture that a test treats as "another chroot" differs in
content from the first one, whatever the clock. The test asserts this
before relying on it, so an identical fixture fails as a fixture error, not
as a product assertion.

## 4. Change

`scripts/tests/test_build_sbuild.py` only:

1. In `test_tested_with`, the other chroot gets a different snapshot stamp:
   `make_chroot(self.base / "other", stamp=stamp_days_ago(2))`. The stamp is
   in `etc/apt/sources.list`, so the tar content differs. Two days is inside
   the 7-day policy and needs no `--allow-old-chroot`. Before the build, add
   `assertNotEqual(sha256(other), sha256(self.chroot))`.
2. New `test_tested_with_same_bytes_elsewhere`: a byte-identical copy of the
   tested chroot (tarball and sidecar, `shutil.copy2`), at another path, is
   accepted. The result is rc 0, `tested_with.chroot_sha256` equals the tested
   sha, and the manifest names the copy's path. This states that the check is
   by content, not by path. It is the case that the flaky run hit by
   accident.

No change to `build_sbuild.py` or `chroot_fixtures.py`.

## 5. Verification plan

- Both tests pass under the frozen clock (`tools/frozen-test.py`). The old
  test fails there (section 1).
- The whole `scripts/tests` suite passes. `test_tested_with` passes 20 times
  in a row.
- Mutation check: if the `tested_sha != chroot["sha256"]` comparison in
  `build_sbuild.py` is removed (temporarily, scratch copy only),
  `test_tested_with` fails. If it is replaced with a path comparison, the new
  test fails.

## 6. Design review

Design Challenger (temporary subagent), round 1: **APPROVE**. Notes for the
Verifier:
- In the first version of `tools/frozen-test.py`, only the 1-day stamp was
  frozen. It now freezes one stamp per age for the whole run, so the 2-day
  path is also covered.
- The new test checks the sidecar copy and the copy's path in the manifest,
  and confirms that no `--allow-old-chroot` is passed.
- Mutations were run only in scratch copies.

## 7. Results (branch `a/UNITY-20261002-001`)

- `runs/02-frozen-fixed.txt`: under the frozen clock, `test_tested_with`
  and `test_tested_with_same_bytes_elsewhere` both pass. Before the change,
  `runs/01-frozen-main.txt` shows `0 != 2`.
- `runs/03-suite.txt`: `scripts/tests` gives 299 passed, 1 skipped, and
  682 subtests passed.
- `runs/04-loop20.txt`: both tests passed 20 times out of 20.
- `runs/05-mutations.txt`: the tests were run against scratch copies of
  `scripts/` and `build/` through `BUILD_SBUILD`:
  - no mutation: 2 passed;
  - comparison removed (`if False:`): `test_tested_with` fails;
  - path comparison instead of sha: `test_tested_with_same_bytes_elsewhere`
    fails.
- `build_sbuild.py` and `chroot_fixtures.py` are unchanged against `main`.

## 8. Verification

Independent Verifier (temporary subagent), on `bae658a`: **PASS**. It re-ran
every check itself:
- On `main`, in a scratch worktree, the frozen-clock run fails with `0 != 2`.
- On the branch, both tests pass under the frozen clock. A probe confirmed
  the freeze: fixtures 1.2 s apart have the same sha at both 1 and 2 days.
- The full suite gives 299 passed, 1 skipped.
- Both mutations fail as expected.
- The diff touches only the test and this directory.

Notes, none blocking:
- `assertNotIn("--allow-old-chroot", chroot_args)` documents intent only,
  because the test builds that list itself.
- `tools/repro.py` also fixes owner and group, but `tools/frozen-test.py`
  does not. This makes no difference within one run.
