# UNITY-20261008-019: taskctl cannot close a package task whose change was released in another task's build

Owner: agent B (builder; no target).

```yaml
task_id: UNITY-20261008-019
component: scripts/taskctl.py (task board)
kind: tool
status: INVESTIGATING
observed: >
  UNITY-20261008-014 was implemented, verified and released inside
  UNITY-20261008-011's hud +unity5 build and publication. taskctl has no
  way to close it: package tasks reach DONE only after PUBLISHED, PUBLISHED
  needs the task's own publish record or published_by, and published_by
  needs the task's own build_sbuild manifest (task_id = the task), which
  -014 does not have. DUPLICATE is reachable only from BACKLOG or
  INVESTIGATING. (UNITY-20261002-013 was named as the same case; it is
  not: it has no code of its own and spans two packages, see round 1.)
expected: >
  a package task whose change is part of another task's published build
  can reach PUBLISHED, then DONE, with evidence that ties its change to
  those published bytes; the usual path stays as strict as it is.
```

## Reading the code (main 097bf49)

- `NEXT` (`taskctl.py:22-33`): REVIEW → {READY_TO_PUBLISH, IMPLEMENTING, BLOCKED, DONE}; READY_TO_PUBLISH → {PUBLISHED, BLOCKED}. `DUPLICATE` is reachable only from BACKLOG and INVESTIGATING.
- DONE (`:561-568`): a package task comes only from PUBLISHED.
- PUBLISHED (`:467-…`) reads the task's own publish record, or with `published_by` another task's.
- `published_by` (UNITY-20260929-023, -20261008-003): `covering_record` (`:265`) reads the write-once record by its sha256. `check_own_build` (`:283`) then requires the task's **own** build manifest (its `task_id`), with the record's bytes or a buildinfo-identical build. Its docstring: "A commit that is only an ancestor of the published one proves nothing about the bytes and is refused."
- That rule is right for `published_by`. There, the task built its own package and claims that build is what shipped. -014 claims less: that its change is in the source of the build that shipped. That claim is proved by the published build's own chain (record → gate → manifest → source commit) plus the change's commits being in that source commit's history.

## Design (for the Design Challenger)

1. **Evidence field `released_in`:** `{task_id, record_sha256, change_commits}`.
   - `task_id`: the releasing task, a full id, not the task itself.
   - `record_sha256`: the sha256 of its write-once publish record.
   - `change_commits`: one or more full 40-hex commit ids in the package source that carry this task's change.
   - `released_in` and `published_by` together are refused.
2. **One new edge:** REVIEW → PUBLISHED, allowed only when the evidence has `released_in`. Unchanged:
   - Without `released_in`, REVIEW → PUBLISHED is refused as now.
   - READY_TO_PUBLISH → PUBLISHED.
   - PUBLISHED → DONE, and "package tasks reach DONE only after PUBLISHED".
   - `published_by`.
3. **Checks at PUBLISHED with `released_in`** (a new `check_released_in`, next to `check_own_build`):
   - a. The task kind is package.
   - b. `read_publish_record(records/<task_id>.json, record_sha256)`: no symlink, read-only, the sha256 and the JSON from the same bytes. The record's `task_id` is the releasing task.
   - c. On the board, the releasing task is PUBLISHED or DONE.
   - d. The evidence's `package` and `candidate_version` equal the record's.
   - e. The task's own `verification_result` is PASS and its `review_status` is REVIEWED or INDEPENDENTLY_REPRODUCED. REVIEW already required this; it is checked again here.
   - f. The gate chain, by the existing PUBLISHED code, with the gate taken from the record (as `published_by` does):
     - the gate is committed in this repository and its sha256 equals the record's;
     - `gate.task_id` is the releasing task;
     - the manifest hash equals the gate's;
     - the record's artifacts equal the manifest's;
     - the switch-time evidence;
     - `confirm_live_publication`: the live snapshot still carries the record's artifacts.
   - g. Every `change_commits` entry is a commit in `gate.source_repo` and an ancestor of, or equal to, `record.source_commit` (`git merge-base --is-ancestor`). The gate already holds that this source commit was pushed and clean.
     - If the repository is missing, or a commit is unknown, it is refused (fail closed).
   - h. `target_verified` and `target_verification_record`, as for every PUBLISHED.
4. **Not in scope:** DUPLICATE from later states, and changes to `published_by`.
5. **Documentation:** ENGINEERING-PROCESS section 6 gets a rule "R. `released_in`" next to rule P. It covers when to use which:
   - P: the task's own build shipped in another task's publication;
   - R: the task's change is in another task's build.
6. **Tests** (`scripts/tests/test_taskctl_released_in.py`, on the fixtures of `test_taskctl_published_by.py`; a temporary git repository for the ancestry):
   - **pass:** REVIEW → PUBLISHED → DONE with a valid `released_in`;
   - **refusals:**
     - the wrong record sha256;
     - a writable record or a symlink;
     - the releasing task is not PUBLISHED or DONE;
     - another package or version;
     - a change commit that is not an ancestor;
     - an unknown commit;
     - a missing source repository;
     - `released_in` together with `published_by`;
     - `task_id` equal to the task itself;
     - no target record;
     - a non-package kind;
   - **regressions:**
     - REVIEW → PUBLISHED without `released_in`;
     - a package task REVIEW → DONE;
     - READY_TO_PUBLISH → PUBLISHED unchanged (the existing tests);
     - `published_by` unchanged (the existing tests).

### Design review, round 1: REVISE (all points taken)

The Design Challenger (an independent subagent) kept the shape: a package
task reaches PUBLISHED through another task's write-once record, then DONE,
and "DONE only after PUBLISHED" stays. Its points, as applied in the
revised design below:

1. **A BLOCKED route to PUBLISHED already exists, with no condition.**
   BLOCKED lists PUBLISHED, and `resume_state` only has to name a state.
   Every `published_by` task got there that way (UNITY-20260927-052,
   -20260928-020 and -20261002-011 have `resume_state: "PUBLISHED"`).
   Adding a NEXT entry alone would not restrict anything. The condition goes
   into `require_evidence` (it already receives the `state`), and the
   `released_in` checks are equally strong from every state.
2. **The PUBLISHED identity loop compares `task_id`, `package`,
   `candidate_version` and `source_commit` with the gate.** The design now
   says which keys `released_in` skips, and that `release_gate` and
   `build_manifest`, when present, must equal the releasing task's.
   `released_in` also becomes a package marker.
3. **The ancestry proof:**
   - **A deletable source repository.** `gate.source_repo` is a task
     worktree, and `/packages/` is git-ignored in base. An optional
     `released_in.source_repo` is accepted when its tree of
     `record.source_commit` equals `gate.source_tree_hash`.
   - **Commits that shipped before.** On hud, `b0c2444` is an ancestor of
     `db26b0d` but shipped in +unity4. Change commits must not be
     ancestors of an earlier publish record's source commit of the same
     package.
   - **Merges and empty commits.** These are refused: a commit must have
     one parent and change at least one file.
   - **Reverts are not checked in code.** A "change still present" test
     would refuse -014 itself: `1fc54e1` does not reverse-apply on
     `db26b0d`. The target record must exercise the change, and rule R
     says so.
   - **Over-engineering, not done:** parsing PATCHES.md, and requiring the
     task id in the commit message (light-locker `40843ef` names no task).
4. **UNITY-20261002-013 is not this case.** It has no code of its own and
   two packages (unity, light-locker, via -015 and -016), and it cannot
   honestly reach REVIEW. It is out of scope here and is closer to
   ALREADY_FIXED (FIXED_LOCAL) from INVESTIGATING. C decides. The card's
   `observed` is corrected.
5. **The releasing task's board state** is read from the rows `main`
   already read under the board lock, with no second read or write. Its
   Verifier result is taken from the pinned gate (`verification_result:
   PASS`), not from its mutable evidence.
6. **The record sha256 pin is enough.** The record pins the gate, and the
   gate pins the manifest. "Committed" is dropped from 3f.
   `read_publish_record`'s message becomes neutral. The ordinary path
   reads its own record without the write-once checks: a follow-up for C.
7. **The pass test could not run as written.** The PUBLISHED branch uses
   `Path.home()`, `parents[1]` and a real `aptly`. The harness is specified
   below, and the missing tests are added.
8. **Documentation:**
   - Rule P's "an ancestor is refused" is reworded "for `published_by`".
   - Section 1's path line, steps 9 and 12, and the BLOCKED route all get
     a line.

## Design, revised after round 1

**Transitions:**
- **NEXT:** REVIEW gains PUBLISHED. Nothing else changes.
- **`require_evidence(PUBLISHED, …)`:**
  - From REVIEW: refused unless the evidence has `released_in`. A
    `published_by` task keeps its present route; letting it use REVIEW →
    PUBLISHED as well, which would retire the BLOCKED workaround, is a
    question for C.
  - From READY_TO_PUBLISH: `released_in` is refused, because that task has
    its own gate.
  - From BLOCKED: unchanged (its own record or `published_by`). With
    `released_in`, all the checks below apply.
  - `released_in` together with `published_by` is refused.
- **PACKAGE_MARKERS** gains `released_in`, so a tool or operation kind with
  it fails at `resolve_kind`.

**`released_in = {task_id, record_sha256, change_commits[, source_repo]}`**
(a new `check_released_in(data, task_id, rows, records_dir, repo)`):

1. **Shape:**
   - `task_id`: a full id, not the task itself;
   - `record_sha256`: 64 hex;
   - `change_commits`: a non-empty list of distinct 40-hex ids;
   - `source_repo`: an optional absolute path.
2. **The record:** `read_publish_record(records/<task_id>.json, record_sha256)`
   (no symlink, read-only, sha256 and JSON from the same bytes), and its
   `task_id` is the releasing task.
3. **The board:** the releasing task's row exists (from `rows`) and is
   PUBLISHED or DONE.
4. **The task's own review:** `verification_record` is present,
   `verification_result` is PASS, and `review_status` is REVIEWED or
   INDEPENDENTLY_REPRODUCED, as required for REVIEW. If
   `independent_reproduction_required`, it must be INDEPENDENTLY_REPRODUCED.
5. **Identity with the record and the gate:**
   - `package` and `candidate_version` are equal.
   - `source_commit` is absent or equal to the record's.
   - `release_gate` is absent or equal to `record.gate_file`.
   - `build_manifest` is absent or equal to the gate's manifest file.
   - In the PUBLISHED identity loop only `task_id` is skipped.
6. **The gate chain**, by the existing PUBLISHED code with the gate from the
   record:
   - its sha256 equals the record's;
   - `gate.task_id` is the releasing task;
   - `gate.verification_result` is PASS;
   - the manifest hash and the record's artifacts match;
   - the switch-time evidence;
   - `confirm_live_publication`.
7. **The repository:** `source_repo` or else `gate.source_repo`. It must
   exist, and `git rev-parse <record.source_commit>^{tree}` must equal
   `gate.source_tree_hash`. Otherwise the transition is refused.
8. **Every change commit:**
   - it is a commit there, with exactly one parent and a non-empty
     `git diff-tree --name-only -r`;
   - it is an ancestor of, or equal to, `record.source_commit`;
   - it is **not** an ancestor of, nor equal to, the `source_commit` of
     any other publish record of the same package with an earlier
     `published_at`. If such an earlier commit is unknown in the
     repository, the transition is refused.
9. **The target:** `target_verified` and `target_verification_record`, as
   for every PUBLISHED. By rule R, the record must exercise this task's
   change on the published version; taskctl does not read its content.

**Documentation (ENGINEERING-PROCESS):**
- **Rule R** describes `released_in`, when to use it rather than P, the
  REVIEW → PUBLISHED edge, the BLOCKED route, the target record, and
  running taskctl from a checkout that holds the releasing task's gate
  (main, after C's merge).
- **Rule P:** "an ancestor is refused" now applies "for `published_by`".
- **Section 1** gets the path line, and **step 12** says that the
  releasing task's branch is the one C merged.

**Tests** (`scripts/tests/test_taskctl_released_in.py`):
- **The harness:** each test copies `taskctl.py` and `tested_build.py`
  into a temporary repository (the gate, the manifest, the evidence) and
  makes a temporary hud-like git repository with commits. It imports that
  copy, sets `HOME` to a temporary home (publish records written 0444,
  `TASKCTL_BOARD`), and replaces `confirm_live_publication` in the
  imported module. No new environment override is added to taskctl.
  Transitions run through `main()`.
- **Accepted:**
  - REVIEW → PUBLISHED → DONE;
  - REVIEW → BLOCKED (`resume_state` PUBLISHED) → PUBLISHED with
    `released_in`;
  - a change commit equal to `record.source_commit`;
  - an alternative `source_repo` with the right tree.
- **Refused:**
  - REVIEW → PUBLISHED without `released_in`;
  - BLOCKED → PUBLISHED with neither field and no own record;
  - READY_TO_PUBLISH + `released_in`;
  - REVIEW + `released_in` → DONE (DONE only after PUBLISHED);
  - a tool kind or tool kind lock with `released_in`;
  - `released_in` together with `published_by`;
  - the task's own id;
  - a wrong record sha256, a writable record, a symlinked record;
  - the releasing row missing, or in READY_TO_PUBLISH or BLOCKED;
  - another package or version;
  - `release_gate`, `source_commit` or `build_manifest` that differ;
  - a short hash, an empty list, duplicates;
  - a merge commit, an empty commit;
  - a commit that is not an ancestor, an unknown commit;
  - a commit that is an ancestor of an earlier record of the same package;
  - a missing repository, and an alternative repository with another tree;
  - the live check failing;
  - no target record;
  - the gate's `verification_result` not PASS.
- **Unchanged:**
  - BLOCKED → PUBLISHED with the task's own record;
  - READY_TO_PUBLISH → PUBLISHED;
  - the existing `published_by` and live-snapshot tests.

### Design review, round 2: APPROVE

Checked against the publish records and the hud clone of -011's gate.

- **-014 is not blocked by the earlier-record check.** The earlier hud records are +unity2 `ef39a8d`, +unity3 `9e7c093` and +unity4 `b0c2444`. All three are commits in that clone and ancestors of `db26b0d`, and `1fc54e1` is an ancestor of none of them.
- **The tree and gate pins hold.** `db26b0d^{tree}` equals `gate.source_tree_hash`, and the gate sha256 equals the record's.
- **The other packages' latest gates have their earlier source commits present** (unity, unity-settings-daemon; light-locker has no earlier record).
- **The known limit:** versions published before publish records existed (hud +unity1) are never checked. Rule R says so.

Implementation details taken into the design:

1. **A test:** REVIEW → PUBLISHED with `published_by` (and no `released_in`) is refused until C decides otherwise.
2. **Two git exit codes:** `git merge-base --is-ancestor` exits 1 for "not an ancestor" and 128 for an unknown object. Every id is first resolved with `git rev-parse --verify <id>^{commit}`, and any exit code other than 0 or 1 refuses. A test covers an earlier record whose source commit is unknown.
3. **Earlier records fail closed:**
   - only files named exactly `UNITY-YYYYMMDD-NNN.json` are read, and the releasing record is skipped by its `task_id`;
   - a record that cannot be read, is not JSON or has a bad `published_at` refuses the transition;
   - `published_at` is compared as a parsed UTC datetime;
   - a test covers an unreadable record of the same package.
4. **The harness:**
   - the copy is imported with `importlib.util.spec_from_file_location` under its own name, not as `taskctl`;
   - it sits at `<tmp>/scripts/taskctl.py`, so that `parents[1]` is the temporary repository;
   - `check_released_in` does not import `tested_build` (which imports `build_dependencies` at load time);
   - `sys.argv` is patched and stderr captured.
5. **-014's evidence before its transition:**
   - `released_in.change_commits` = [`1fc54e15eedd51e04e26cac549d29487dd650008`];
   - `release_gate` exactly `record.gate_file`, or removed.

## Implementation (2026-10-08)

Branch `b/UNITY-20261008-019`:

- **`scripts/taskctl.py` (`4dbd078`):**
  - `released_in` is a package marker, and NEXT REVIEW gains PUBLISHED.
  - `released_in_record` checks the shape, the board row of the releasing
    task (from the rows `main` read under the lock), the write-once record
    by sha256, the task's own review, and the package and version.
  - `check_released_commits` checks the repository and its tree, the
    earlier records of the package (fail closed), and each change commit:
    one parent, files changed, in the published source, in no earlier
    publication.
  - **The PUBLISHED branch:**
    - REVIEW without `released_in` is refused;
    - READY_TO_PUBLISH with `released_in` is refused;
    - `released_in` and `published_by` exclude each other;
    - the gate comes from the record, its `verification_result` must be
      PASS, and `build_manifest` and `release_gate` must be absent or
      equal;
    - only `task_id` is skipped in the identity loop, and `source_commit`
      when absent.
  - `read_publish_record`'s message is neutral ("named in published_by or
    released_in").
  - `require_evidence` takes the board rows.
- **`scripts/tests/test_taskctl_released_in.py`:** 45 tests on the harness
  of round 2. They cover:
  - accepted: REVIEW → PUBLISHED → DONE, the BLOCKED route, a change
    commit equal to the published one, an alternative repository, the
    matching optional fields, a DONE releasing task;
  - every refusal of the design, including REVIEW → PUBLISHED with
    `published_by`, an earlier record with an unknown commit, an
    unreadable earlier record, and other files in the records directory.
- **`docs/ENGINEERING-PROCESS.md`:** rule R; rule P's ancestor sentence
  "for `published_by`"; the path line in section 1; step 12.
- **Tests:** all of `scripts/tests` pass (397 passed, 1 skipped; before
  the change 352 + 1 skipped).

## Verification, round 1: FAIL (fixed)

The Verifier (independent subagent) checked the following and found
nothing wrong in them:
- the diff against the design;
- every transition reachable without `released_in` (unchanged);
- the round-2 details;
- the whole suite;
- mutation tests;
- the dry check, which is byte-identical.

One blocking finding: the repository the ancestry is checked in is a
working tree anyone can change, and git's own history-override settings in
such a repository were trusted. With them, a commit that was never
published, or one that shipped earlier, could pass. Forged objects
themselves fail closed, because git verifies object hashes. The change
existed only on this task branch and never reached main.

Fix:
- `git_out` runs git with replace refs, grafts and the commit-graph file
  switched off, and without inherited `GIT_*` settings;
- a shallow repository is refused;
- an earlier record with the same `published_at` counts as earlier.

Tests:
- seven new tests, one for each such override (in the evidence's
  repository, in the gate's, hiding an earlier publication, grafts in the
  repository and from the environment), a shallow repository, and the
  equal timestamp;
- run against the version before the fix, exactly these seven fail.

Also from the Verifier's remarks:
- the own `review_status` check now has a test;
- the tree test now says what it tests (the gate's tree must agree with
  the repository's; a repository holding the published commit always has
  its tree);
- rule R says what is trusted in the repository, and that a change commit
  is not tied to the task by the tool (the task's Verifier checks that).

`scripts/tests`: 405 passed, 1 skipped. The dry check on
UNITY-20261008-014 is unchanged.

## Verification, round 2: FAIL (fixed)

The Verifier confirmed the following:
- the round-1 fix, and its seven tests against the version before it;
- that its own round-1 cases are now refused;
- that a crafted commit-graph, the repository's own config, a `.git` file
  pointing elsewhere and a sha256 repository gain nothing;
- the whole suite and the dry check.

One blocking finding: git verifies the hash of a commit that is named
directly, but not of the commits an ancestry walk passes through. A
repository could therefore hold, under a real intermediate commit's id, an
object that does not hash to it (loose, packed or behind alternates).
`git fsck` notices such an object; `merge-base` does not. The change was
still only on this task branch.

Fix: taskctl walks the history itself (`VerifiedHistory`):
- one `git cat-file --batch` process reads each commit on the way raw;
- the sha1 of `commit <size>\0<body>` must equal the id;
- the tree and the parents are taken only from verified bodies;
- `merge-base` and `rev-list` are no longer used for these checks;
- this covers the published commit's tree, the single-parent check, the
  ancestry, and the earlier-publication check.

Tests:
- four new tests: a forged intermediate commit loose, packed and behind
  alternates, and one hiding an earlier publication;
- run against the round-2 version, exactly these four fail.

`scripts/tests`: 409 passed, 1 skipped. The dry check on
UNITY-20261008-014 is unchanged. Rule R says the history is walked and
verified by taskctl.

## Verification, round 3: FAIL (fixed)

The Verifier confirmed:
- the round-2 fix, with its four tests failing against the version before
  it;
- that all its earlier cases are refused;
- the walk's speed on the unity history (about 0.1-0.2 s for ~420
  commits);
- that SHA-1 collisions are out of scope;
- the dry check.

One blocking finding: git reads the source repository's own configuration,
and some settings there name programs that git runs, even for the read-only
calls taskctl made. A taskctl transition is an allowed command, so this
must not be possible. The change was still only on this task branch.

Fix:
- **The settings:** git runs with fsmonitor off, no transport protocol
  allowed, hooks pointed nowhere, and `GIT_NO_LAZY_FETCH`.
- **Partial clones:** a repository configured as one (`extensions.partialClone`
  or a promisor remote) is refused.
- **Fewer git calls:** taskctl no longer calls `diff-tree` ("changes files"
  is now "the tree differs from its parent's tree", from verified bodies)
  or `rev-parse --verify` (ids must be full 40-hex, and `cat-file`
  checks the type). Only `rev-parse --is-shallow-repository`, `config
  --get-regexp` and `cat-file --batch` are left.
- **Commit parsing as git does it:** `tree` first, then only consecutive
  `parent` lines, then `author`, and no `tree` or `parent` line later in
  the header. This follows the Verifier's remark.

Tests: five new tests.
- A configured fsmonitor does not run.
- A partial clone is refused and fetches nothing.
- A missing object fetches nothing. This one already passed before the fix.
- Two malformed but correctly hashed commits are refused (an extra parent
  after `committer`, a parent before the tree).

Against the round-3 version, exactly four of them fail.

`scripts/tests`: 414 passed, 1 skipped. The dry check on
UNITY-20261008-014 is unchanged. Rule R says what git may still do.
