# UNITY-20260929-014: build_dependencies hardening (from UNITY-20260929-013 Verifier round 2)

Tool task, agent A. Parent: UNITY-20260929-013 (`build_sbuild.py
--extra-package`, the manifest's `build_dependencies`, checked by
`create_release_gate.py` and `publish_aptly.py`). Its Verifier round 2 passed
and left four non-blocking remarks; this task closes them.

## 1. Reproduction on main (`02e0af8`)

`tools/repro.py <checkout>` (`runs/repro-main-02e0af8.txt`):

| # | Remark | On main |
|---|---|---|
| R1 | the manifest directory's `build-dependencies/` is a symlink to a directory elsewhere | `check_entries` ACCEPTS: each file is checked against the *resolved* `build-dependencies/`, so the copies need not sit next to the manifest |
| R2 | `size: true` | ACCEPTED: `isinstance(True, int)` |
| R3 | `extra_packages()` refuses a package (here a foreign architecture) | refused, but `build-dependencies/libfoo_1.0_armhf.deb` is LEFT in the output: it copies each file before reading its fields |
| R4 | consumers | `ConsumerTest` only checks the text of the two scripts for the call; no run shows that a real `create_release_gate.py` / `publish_aptly.py` refuses a bad `build_dependencies` |

The pool guarantee (the same bytes in `/srv/aptly/public/pool`) holds in all
four; what R1 loses is "the copy that sbuild got sits next to the manifest",
R2 a record field's type, R3 a clean output after a refusal, R4 proof at the
consumer level.

## 2. Existing fix

Own tool, own code of 2026-09-29: nothing in main after `2de93ad` touches
`build_dependencies.py` or `extra_packages()`; no other task on the board
covers it. `NOT_FIXED`.

## 3. Root cause

- R1: `check_entries` resolves `base / "build-dependencies"` and compares the
  file with the resolved directory; it never asks whether that directory
  *is* `base/build-dependencies`.
- R2: the type check uses `isinstance(..., int)`, and `bool` is a subclass
  of `int`; the size is not compared with the file either.
- R3: `extra_packages()` does path checks and the copy in one loop per file,
  and reads the Debian fields from the copy (by design: the bytes sbuild
  gets); every refusal after a copy returns without removing it.
- R4: the consumer test was textual (Verifier round 2 remark).

## 4. Approach

- R1: refuse unless `base/build-dependencies` resolves to itself (no symlink
  on the way; `base` is already resolved), and each file lies inside it.
- R2: `size` must be a non-negative `int` that is not a `bool`, and equal to
  the file's size.
- R3: first all path checks for every `--extra-package` (nothing copied),
  then copy into `build-dependencies.partial/` in the output, read and check
  the fields there, rename to `build-dependencies/` only when every package
  passed; on any refusal remove the partial directory. The copy stays the
  bytes sbuild gets and the manifest hashes (unchanged design of -013).
- R4: `scripts/tests/test_build_dependencies_consumers.py` runs the real
  `create_release_gate.py` and `publish_aptly.py` in a temporary copy of the
  repository (git, a local "remote", a package checkout under `packages/`, a
  fake HOME with a board and task evidence). A bad `build_dependencies` must
  be refused with the dependency message; a good one must pass the check
  and stop at the next step. Safety: `PATH` starts with a fake `aptly`
  that only records its arguments and exits 1, the test asserts that
  `aptly` resolves to it, and HOME is the temporary directory; the refusal
  cases must leave the fake's log empty.

Correct layer: `build_dependencies.py` is the one check both consumers call;
`extra_packages()` is the one place that creates the copies.

Not in scope: the pool guarantee and the consumers' order of checks
(unchanged).

## 5. Implementation and validation

Code `7a2afea` (branch `a/UNITY-20260929-014`, on main `02e0af8`):

- `build_dependencies.check_entries`: refuses unless `build-dependencies/`
  in the manifest directory is itself a directory, not a symlink, and
  resolves to itself; `size` must be an `int` that is not a `bool`, not
  negative, and equal to the file's size (checked after the sha256).
- `build_sbuild.extra_packages`: split into `extra_package_paths` (all path
  checks, nothing copied) and `copy_and_check` (copy, fields from the copy);
  the copies go to `build-dependencies.partial/`, renamed to
  `build-dependencies/` only when every package passed, removed on a
  refusal or an exception.
- `scripts/tests/test_build_dependencies_consumers.py`: the real
  `create_release_gate.py` and `publish_aptly.py` in a temporary repository
  (section 4). A good `build_dependencies` gives the same exit code and
  message as a manifest without the key; a wrong sha256, `size: true`, a
  file missing from the pool, and a symlinked `build-dependencies/` are
  each refused with the dependency message. The fake `aptly` log stays
  empty in every case.
- Existing fixture fix: two tests in `test_build_dependencies.py` reused the
  first package's `size` for another file; they now record the file's own
  size (with the new size check they failed whenever the two sizes
  differed).

Results:

- The new and changed tests on main's scripts fail 16 times
  (`runs/new-tests-on-main-02e0af8.txt`: R1 1, R2 3, R3 8, consumers 4 =
  size and symlink for each consumer; the sha256 and pool cases already
  pass on main). On the branch: full suite 200 tests OK (1 skipped), three
  consecutive runs of the two changed modules OK.
- `tools/repro.py` on the branch: R1 and R2 REFUSED, R3 CLEAN
  (`runs/repro-fixed.txt`).
- Real runs (`tools/run-real.sh`, `runs/run-real.log`): Q1 a real sbuild of
  `tiny013` with our pool's `libnux-4.0-common` exits 0, with
  `build-dependencies/` and no `.partial` in the output, `manifest_error`
  None; Q2 the same plus an arm64 package exits 2 before sbuild, and the
  output directory stays empty; Q3 the UNITY-20260927-040 gated manifest
  under the new check (real pool) returns None.

## Verification

Independent temporary Verifier subagent (`.claude/agents/adversarial-verifier.md`),
round 1 on `7a2afea`: **PASS** (`PATCH_CORRECT`), `INDEPENDENTLY_REPRODUCED`.
It ran the new and changed tests itself on main's scripts (38 tests, 16
failures, as recorded) and on the branch (all pass; full suite 200 OK);
probed R1 (symlinked directory, a symlinked subdirectory or file inside it:
refused; manifest directory through a symlink, relative path: accepted),
R2 (`1.0`, `None`, `False`, text, a list: refused; a huge int by the size
comparison), R3 (junk `.deb`, an exception after the copy, `dpkg-deb`
missing: output empty, no `.partial`), and R4 (fake `aptly` always first,
bare `aptly` calls only, every case stops before the first call; the real
scripts with only the pool line replaced).

Remarks, not blocking:

- A refusal after sbuild has run (copy changed during the build, no
  `.buildinfo`, package not used, an sbuild failure) leaves
  `build-dependencies/`, the sbuild log and sbuild's result files in the
  output, and writes no manifest - as since UNITY-20260929-013. The output
  directory is single-use (a non-empty one is refused), so this is harmless;
  this task only covers refusals before sbuild.
- `rmtree(..., ignore_errors=True)` can leave a `.partial` on a permission
  error, and a SIGKILL leaves one; the next run refuses the non-empty output
  directory either way.
- The directory check and the file reads are separate path lookups (no
  directory handle); a swap in between is out of scope for our own build
  tree.
- A wrong-typed `size` is reported as "lacks one of ..."; no unit test
  injects an exception into `extra_packages` (probed only).

## Outcome

`REVIEW` (tool task): the four remarks of UNITY-20260929-013's Verifier
round 2 are closed. Branch `a/UNITY-20260929-014` for the coordinator to
merge; `DONE` after the merge.
