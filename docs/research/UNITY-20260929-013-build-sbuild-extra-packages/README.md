# UNITY-20260929-013: build_sbuild.py cannot build a package that needs our own build dependencies

Blocker of UNITY-20260927-040. `scripts/build_sbuild.py` is the only approved
way to build a package for publication (ENGINEERING-PROCESS section 6: it
writes the build manifest that the release gate, `publish_aptly.py`,
`version_safety.py` and `taskctl.py` check). It runs plain `sbuild -d SERIES`
in the shared resolute chroot, whose apt sees only the Ubuntu archive. unity
cannot be built that way. Agent A, 2026-09-29.

## 1. Reproduction

`python3 scripts/build_sbuild.py --task-id UNITY-20260927-040 --source-repo
~/work/a/040-unity --target-series resolute --output-dir ...` on unity
`7b0eca27` (`+unity12`): exit 2, `sbuild failed (2)`; the log
(`from-040/build_sbuild-failed-nux.log.xz`)
ends in `dh_auto_configure: error` after

    Package 'libpcre', required by 'nux-4.0', not found
    CMake Error ... The following required packages were not found: - nux-4.0>=4.0.5

FACT: the archive's `libnux-4.0-dev` `4.0.8+18.10.20180623-0ubuntu12` ships a
`nux-4.0.pc` that requires `libpcre`, which resolute no longer has (DECISIONS
2026-09-22 "nux -0ubuntu13": LP #2147013; the fixed revision was never
uploaded to resolute). Our repository carries fixed nux (`0ubuntu13`,
`0ubuntu15+unity1`, `0ubuntu15+unity2`, which target runs). The same source
builds with plain `sbuild --extra-package` for our three nux `.deb`s
(`Status: successful`, 503 s,
`from-040/test-build-extra-package-nux.log.xz`),
and unity was built the same way before build_sbuild.py existed (DECISIONS
2026-09-22). So the defect is the tool's: it has no way to give sbuild an
input beyond the archive, and a build that needed one could not be recorded.

## 2. Existing fix

This repository: no option in `build_sbuild.py` (192 lines, arguments
`--task-id --source-repo --target-series --output-dir`), none in its tests
(`scripts/tests/test_build_sbuild.py`), no other build wrapper under
`scripts/`; `~/.sbuildrc` and `~/.config/sbuild/config.pl` set no extra
packages or repositories (a global setting would also be unrecorded and
apply to every build). Nothing on the task board or in DECISIONS changes it.
It is our own tool: no upstream to search.

## 3. Design

Invariant: a build manifest records everything the build used that the
target series' archive and the source commit do not already pin: which extra
package, from where, and its exact bytes (sha256). A build without extra
inputs behaves - and its manifest reads - exactly as before.

Candidates:

- **E1 `--extra-package PATH` (repeatable).** Each path must be a `.deb`
  file. build_sbuild.py reads Package/Version/Architecture with `dpkg-deb`,
  copies the file into `OUTPUT/build-dependencies/`, hashes the copy, and
  passes the copy to sbuild as `--extra-package=`, so the bytes recorded are
  the bytes used. The manifest gets a new optional top-level list
  `build_dependencies` (file, sha256, size, package, version, architecture,
  the path it was taken from, and whether that path is in our published
  repository's pool). The copies are re-hashed after the build; a change
  fails the build. `artifacts` is unchanged, so every consumer that reads it
  (publish_aptly's one-rule-per-kind contract, version_safety, apt_view,
  taskctl's publish-record comparison, create_release_gate) sees exactly
  what it saw before; `schema` stays 1.
- **E2 `--extra-repository URL`** (our repository, as sbuild's
  `--extra-repository` + key). Not pinned: what apt picks depends on the
  repository's state at build time, and the manifest would have to record the
  resolved package versions and hashes after the fact from the build log.
  Rejected for the manifest's purpose; E1 needs no network trust either.
- **E3 put our nux into the chroot tarball.** Every build would then use an
  unrecorded non-archive package; the tarball is shared and read-only
  (TWO-AGENTS). Rejected.
- **E4 get nux 0ubuntu13 into resolute (SRU, LP #2147013).** Right in the
  long run and already pursued through the coordinator, but outside our
  control and time; does not remove the need to record extra inputs.
- **E5 record extra packages inside `artifacts` with a new kind.**
  publish_aptly rejects unknown kinds (or would need a new rule), and the
  release record compares the artifact list: every consumer would need a
  change. Rejected in favour of a separate key.

Chosen: E1, revised after Design Challenger review 1 (section 4).

## 4. Design as revised (review 1)

sbuild 0.91.2ubuntu3 (`Sbuild/ResolverBase.pm`, `Build.pm`, read by the
reviewer): `--extra-package` puts the files in a temporary trusted local
archive with no pin; apt picks the highest version across all sources. An
extra package that is not newer than the archive's is silently not used,
and sbuild only skips or warns on a duplicate basename, a wrong
architecture, a non-file path, and reads every `.deb` of a directory. So
recording the input is not enough: the manifest must record what was used,
and the consumers must check it.

- **Before sbuild runs** (after the empty-output check), every
  `--extra-package PATH` is resolved against the caller's directory
  (symlinks followed; path as given and resolved path recorded) and refused
  unless: a regular readable file named `*.deb`; `dpkg-deb` reads Package,
  Version, Architecture, Source; not `Package-Type: udeb`; Architecture
  `all` or the build architecture; no duplicate basename, resolved file, or
  package+architecture. Refusal: exit 2, sbuild not started, no manifest.
- The file is copied to `OUTPUT/build-dependencies/`, the copy hashed and
  passed to sbuild by absolute path. `in_our_repository_pool` is decided by
  content: the pool file for the package (`pool/main/<initial>/<source>/<file>`
  under the published tree, read as a file) exists and has the same sha256;
  its path is recorded as `pool_path`.
- **After a successful build**: every copy is re-hashed (mismatch: exit 2,
  no manifest), and every dependency must appear as `package (= version)` in
  the `.buildinfo`'s `Installed-Build-Depends` (missing or other version:
  exit 2, no manifest) - "recorded" becomes "recorded and used".
- The log header uses `shlex.join` (same bytes for today's command).
- Manifest: optional `build_dependencies` list, only with the option; each
  entry file (relative, under `build-dependencies/`), sha256, size, package,
  version, architecture, source, given_path, resolved_path,
  in_our_repository_pool, pool_path. `artifacts` and `schema` unchanged.
- **Consumers** (only when the key is present; a manifest without it behaves
  exactly as today): `create_release_gate.py` and `publish_aptly.py` both call
  one shared check (`scripts/build_dependencies.py`): the key is a list of
  entries with the required fields; `file` is relative and resolves inside
  the manifest's directory; the copy exists and matches its sha256; the
  bytes are in our published pool (same file, same sha256). The pool
  requirement keeps a published build reproducible from inputs we publish.

Conditions of review 2 (APPROVE), built in:

1. Pool path as Debian lays it out: `pool/main/<prefix>/<source>/` with
   prefix = first four letters for `lib*` sources, else the first letter;
   source from the `.deb`'s `Source` field without its `(version)` part, the
   package name when the field is absent; file name the canonical
   `package_version-without-epoch_arch.deb`, not the basename passed in.
2. "Our published pool" is `/srv/aptly/public/pool` only (read as files;
   `/srv/aptly/public/candidate/` is unpublished staging and does not
   count). The root is defined once in `scripts/build_dependencies.py`, with
   a parameter the tests override. Consumers recompute the pool path from
   package, source, version and architecture and do not trust the recorded
   `pool_path`; they also refuse a recorded `pool_path` outside the root.
3. `.buildinfo` `Installed-Build-Depends`: a multi-line field, one
   comma-separated entry per line, entries possibly `name:arch (= version)`;
   name, qualifier and version compared exactly. `--extra-package` used and
   no `.buildinfo` in the `.changes`: exit 2.
4. (rationale corrected above: reproducibility, not versioned runtime
   dependencies - unity's `Depends` names `libnux-4.0-0` without a version.)
5. Build architecture = `dpkg --print-architecture` on the host (sbuild's
   default); an extra package must be `all` or that.


Consumers checked (FACT, code): `create_release_gate.py` reads task_id,
package, candidate_version, target_series, result, schema, source_repo,
source_commit, source_tree_hash and `artifacts` (hash re-check) and hands the
manifest to version_safety.py; `publish_aptly.py` reads the same identity
fields, timestamps, `log` and `artifacts` (one rule per `kind`, unknown kinds
rejected); `version_safety.py` and `apt_view.py` read package,
candidate_version, source_commit and binary `artifacts`; `taskctl.py`
compares the publish record's artifact list with the manifest's
`artifacts`. None iterates over top-level keys.

## Evidence card

```yaml
task_id: UNITY-20260929-013
task_kind: tool
issue: local - build_sbuild.py has no recorded way to add build dependencies from outside the archive; unity (nux) cannot be built
status: REPRODUCED
issue_search_result: NOT_FOUND   # our own tool; repository, board, DECISIONS searched (section 2)
source_commit: unity-distro main 60204b8 (scripts/build_sbuild.py as of UNITY-20260928-007)
observed: build_sbuild.py on unity 7b0eca27 fails in configure (nux-4.0 needs libpcre); no option can supply our nux
expected: a package that needs our own build dependency can be built by build_sbuild.py, and the manifest records that dependency (what, from where, sha256)
reproduction: build_sbuild.py --task-id UNITY-20260927-040 --source-repo ~/work/a/040-unity --target-series resolute --output-dir NEW (log in section 1)
root_cause: >-
  build_sbuild.py runs a fixed sbuild command (sbuild -d SERIES
  --no-clean-source --verbose --dpkg-source-opt=-i --dpkg-source-opt=-I);
  the chroot's apt sees only the archive, whose nux is broken, and the tool
  offers no recorded way to add our package
root_cause_mechanism: fixed command line in main(); no argument, no manifest field for extra inputs
root_cause_evidence: scripts/build_sbuild.py:57-93 (arguments, command), the failed unity log (section 1)
invariant: >-
  the manifest records every build input beyond the archive and the source
  commit (package, origin path, sha256 of the exact bytes used) and that it
  was used (.buildinfo Installed-Build-Depends); a publishable build depends
  only on extra packages from our published pool; without
  extra inputs, command and manifest are unchanged; artifacts and their
  consumers are unchanged
existing_fix_result: NOT_FIXED
existing_fix_evidence: section 2 - no option in build_sbuild.py or its tests, no other wrapper, no global sbuild setting
candidate_approaches: [E1 --extra-package recorded in build_dependencies, E2 --extra-repository, E3 chroot tarball, E4 SRU, E5 new artifact kind]
chosen_approach: E1 as revised in section 4 (validation before sbuild, copies hashed and re-hashed, .buildinfo check, pool by content; create_release_gate and publish_aptly check the optional key through scripts/build_dependencies.py)
correct_layer: build_sbuild.py is the one approved builder and the only writer of the build manifest; recording a build input belongs where the command is built and the manifest written
defensive_workaround_rejected: E3 (hidden global input), E5 (touches every consumer's contract), a per-task manual sbuild (no approved manifest)
architectural_task: false
design_challenger_required: true
design_review_result: APPROVE   # review 1: REVISE (use not proven, consumers must check, pool by content, edge cases, tests); review 2: APPROVE with five conditions (section 4)
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked - manifest schema 1 gains an optional key; CLI gains an optional repeatable argument; create_release_gate and publish_aptly validate the key only when present; new module scripts/build_dependencies.py
unknowns: []
test_plan: >-
  scripts/tests/test_build_sbuild.py (stub sbuild writes its argv to a file;
  its .buildinfo gets Installed-Build-Depends from the spec): one
  --extra-package=<absolute copy in OUTPUT/build-dependencies> per input in
  order and build_command equal to that argv; manifest entries with the copy's
  sha256; .buildinfo at another version or missing -> exit 2, no manifest; a
  copy changed during the build -> exit 2, no manifest; without the option:
  build_command exactly today's list, manifest exactly today's key set, no
  build-dependencies/ directory, same log header; every refusal (missing file,
  directory, non-.deb, .ddeb, udeb Package-Type, wrong architecture, dpkg-deb
  failure, same basename twice, same file twice, same package+arch twice) ->
  exit 2 before sbuild (stub never invoked); relative path, symlink and a path
  with spaces accepted and recorded; in_our_repository_pool true/false by
  content with a fake pool. New tests for scripts/build_dependencies.py and
  the publish contract: a manifest with build_dependencies passes; tampered
  copy, missing copy, malformed list, absolute or '..' path, bytes not in the
  pool -> refused; without the key unchanged. taskctl publish-record test
  unchanged with the key present. The whole suite before/after. Real run:
  unity 7b0eca27 with the three 0ubuntu15+unity2 nux .debs from the pool ->
  manifest, .buildinfo shows them, create_release_gate's dependency check
  accepts it; and one extra package older than the archive's -> refused by
  the .buildinfo check. Review 2 adds: a lib* source resolved to its libX/
  pool directory; a .deb only in candidate/ refused; a manifest whose
  pool_path points outside the pool root refused by the consumers.
```

## 5. Implementation and validation

Commit `7939c8f` on `a/UNITY-20260929-013` (7 files, +611/-9):
`scripts/build_dependencies.py` (new: POOL_ROOT, source name, pool path,
content check, `.buildinfo` parser, `check_entries`, `manifest_error`);
`scripts/build_sbuild.py` (`--extra-package`: validation before anything is
copied or built, copies in `OUTPUT/build-dependencies/`, sbuild gets the
copies, re-hash and `.buildinfo` check after the build, optional
`build_dependencies` in the manifest, log header with `shlex.join`);
`create_release_gate.py` and `publish_aptly.py` (one call to
`manifest_error` after their artifact hash check); tests; ENGINEERING-PROCESS
section 6 (a paragraph on extra build dependencies).

**Tests** (`real-runs/suite-branch.txt`): the whole suite 175 OK, 1 skipped
(main: 158 OK, 1 skipped - the 17 new tests are the difference).
`test_build_sbuild.py` 20 tests (12 existing unchanged, 8 new);
`test_build_dependencies.py` 9 new. Against main's build_sbuild.py
(`BUILD_SBUILD=`, `real-runs/new-tests-on-main-build_sbuild.txt`): 7 of the
new tests fail - recorded/used, lib* prefix, not used (2 cases), no
.buildinfo, copy changed, relative/symlink/space; the no-option test passes
on both (unchanged behaviour), and the refusal test passes on main only
because main's argparse rejects the unknown option (exit 2 before sbuild).

**Real sbuild runs** with the new tool (`real-runs/run-real.log`):

| Run | Input | Result |
|---|---|---|
| R1 | tiny013 (Build-Depends: libnux-4.0-common) + libnux-4.0-common repacked as `0ubuntu11`, older than the archive's `0ubuntu12` | exit 2, "was not used by the build (Installed-Build-Depends: ...0ubuntu12)", no manifest - sbuild's unpinned apt took the archive's, and the tool refused |
| R2 | tiny013 + libnux-4.0-common `0ubuntu15+unity2` from the pool | exit 0; `build_dependencies` 1 entry, `in_our_repository_pool: true`, `pool_path` `.../pool/main/n/nux/...`; `manifest_error` with the real pool: none (`real-runs/r2-tiny013-build-manifest.json`) |
| R3 | unity `7b0eca27` (UNITY-20260927-040) + libnux-4.0-0/-common/-dev `0ubuntu15+unity2` from the pool | exit 0, 14 artifacts; all three in `build_dependencies`, in the pool; `.buildinfo` lists the three at `0ubuntu15+unity2` (`real-runs/r3-buildinfo-nux.txt`); `manifest_error` with the real pool: none; manifest keys = today's + `build_dependencies` (`real-runs/r3-unity-build-manifest.json`, log `real-runs/r3-unity-sbuild.log.xz`) |

**Verifier round 1: FAIL (FIX_PARTIAL), fixed in `94341a1`.** The pool
check could be steered by the manifest's own name fields: `source` (or
package/version/architecture) containing `/` or `..` made the computed pool
path point at the unpublished `candidate/` or at the manifest's own copy, and
`check_entries` accepted it; `build_sbuild.py` took `Source` from the `.deb`
unchecked. Fix: every name field must be a valid Debian package name,
version and architecture (`field_error`, both in build_sbuild and the
consumers), and the computed pool path must resolve inside the pool root
(`in_pool`). Remarks also taken: non-string fields refused with a message;
the fields are read from the copy, not the original; a second file of the
same package is refused in any architecture; a consumer entry must be under
`build-dependencies/`; docs wording. New tests: both counterexamples,
non-string fields, file outside `build-dependencies/`, a pool symlink out of
the root, `field_error` cases; in build_sbuild: a `.deb` with
`Source: ../../../etc` and the same package in `all` and `amd64` refused
before sbuild. Suite 180 OK (1 skipped); against main's build_sbuild.py the
same 7 new tests fail (`real-runs/new-tests-on-main-build_sbuild.txt`).
Real runs repeated on `94341a1` (`real-runs/run-real-2.log`): R1 refused
("was not used by the build (Installed-Build-Depends: ...0ubuntu12)"), R2
and R3 exit 0, all dependencies in the pool, `manifest_error` with the real
pool: none (manifests and the R3 log in `real-runs/` are those of this rerun).

Not exercised end to end: `create_release_gate.py` and `publish_aptly.py`
as whole programs on R3 (the gate needs a task in REVIEW, a pushed source in
`packages/`, a version check against a snapshot; the publisher a gate) - their
new line is one call to `manifest_error`, tested directly and checked by
`test_build_dependencies.ConsumerTest`. taskctl's publish-record comparison
reads only `artifacts` (taskctl.py ~l.331); it has no fixture test with a
manifest file, so this is from the code.

## Verification

Independent temporary Verifier subagent (`.claude/agents/adversarial-verifier.md`).

1. **FAIL** (REVIEWED, FIX_PARTIAL) on `7939c8f`: the pool check could be
   steered by `..`/`/` in the manifest's name fields (section 5).
2. **PASS** (REVIEWED, PATCH_CORRECT) on `94341a1`: its counterexamples and
   new probes refused (candidate/ by traversal, own copy, pool file or pool
   directory symlinked out of the root, `Source: ../../etc`, same package in
   two architectures); the new tests fail on `7939c8f` (6 fail, 6 error) and on
   main's tool (7), pass on `94341a1`; suite 180 OK; real runs R1-R3 re-checked
   byte for byte; the path without `--extra-package` untouched. Not blocking:
   `ConsumerTest` is textual (the call is one line, the function is tested);
   build_sbuild imports the new module.

## Outcome

`DONE` (tool task): `build_sbuild.py --extra-package` records extra build
dependencies (what, from where, sha256, used per `.buildinfo`, in our
published pool), and `create_release_gate.py` / `publish_aptly.py` check them
when present; without the option nothing changes. Branch
`a/UNITY-20260929-013` for the coordinator to merge (`94341a1` code, records
after it). It unblocks UNITY-20260927-040 (unity +unity12 builds with our nux,
R3).

Proposed follow-up (ID from C), minor, from Verifier round 2: refuse a
`build-dependencies/` that is itself a symlink out of the manifest's
directory (the pool guarantee holds, only "the copy sits next to the
manifest" is lost); refuse a boolean `size`; optionally copy after the path
checks only (a refused run leaves copies in an output directory that is
single-use anyway); an end-to-end fixture for the two consumers.

