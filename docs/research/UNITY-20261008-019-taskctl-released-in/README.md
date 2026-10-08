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
  INVESTIGATING. UNITY-20261002-013 (light-locker) is the same case.
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
