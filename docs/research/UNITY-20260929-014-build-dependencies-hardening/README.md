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
