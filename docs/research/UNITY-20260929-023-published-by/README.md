# UNITY-20260929-023 - PUBLISHED through another task's publish record

Kind: `tool` (`scripts/taskctl.py`). Owner: B.

## Reproduction

UNITY-20260928-020 and UNITY-20260927-027 are one package version, nux
4.0.8+18.10.20180623-0ubuntu15+unity3. It was published once, under -027:

- `~/coordinator/publish-records/UNITY-20260927-027.json`;
- snapshot `unity-resolute-20260927-027`.

`taskctl.py transition UNITY-20260928-020 PUBLISHED` cannot succeed:

- it reads only `publish-records/<own task id>.json`, which does not exist;
- it requires the task's own `release_gate`;
- it requires the gate's `task_id` to equal the task's.

(hud is not such a case: UNITY-20260927-029 is +unity2 and UNITY-20260927-028
is +unity3. Being included in a later version is not being published, so
-029 closes another way. That is for C to decide.)

## Existing fix

`NOT_FIXED`. main d5e24e3 has only the per-task record path.

## Root cause

The PUBLISHED gate assumes one publish record per task. When one
publication carries several tasks of the same package version, there is
no way for the other tasks to cite it.

## Invariant

A task reaches PUBLISHED only on a publish record that:

- the publisher wrote once;
- is live;
- carries this task's package version.

## Chosen approach (after the Design Challenger's round 1, REVISE)

The evidence gains `published_by: {"task_id": T, "record_sha256": H}`. With
it, the PUBLISHED gate uses `publish-records/T.json` and refuses unless all
of these hold:

1. **The record.** T is not the task itself. The record is read once:
   - it is opened with `O_NOFOLLOW` and checked with `fstat` on that
     descriptor: a regular file with no write bit (the publisher writes it
     `0444` with `O_EXCL`);
   - the sha256 of the same bytes is H, and those bytes are parsed.
2. **Record and gate.** The release gate is the one the record names
   (`gate_file`, `gate_sha256`), as today. `task_id`, `package`,
   `candidate_version` and `source_commit` must agree between the record
   and the gate, and both `task_id` values are T. The task's own
   `release_gate` is not required; if it is set, it must be that file.
3. **The task and the record.** The evidence's `package` and
   `candidate_version` equal the record's.
4. **The task's own build proves its change is in the published source.**
   `build_manifest` is required.
   - The manifest's `task_id` is this task, and its `package` and
     `candidate_version` equal the record's.
   - Its `source_commit` equals the record's `source_commit`, or is an
     ancestor of it (`git -C <manifest source_repo> merge-base
     --is-ancestor`). Both must be full 40-hex commits, and the record's
     commit must exist in that repository.
   - The evidence's own `source_commit` is not used; it may be free text,
     as for -020.
5. **Artifacts.** The manifest's `source` and `binary` artifacts and the
   record's are the same set of (file name, package, version,
   architecture), in both directions. The sha256 may differ, because it is
   a different build of the same source. The record's hashes are checked
   against the live snapshot in rule 6.
6. **Unchanged:**
   - the gate's build manifest against the record's artifacts;
   - the switch-time evidence and the timestamp;
   - the task's own `target_verified` and `target_verification_record`;
   - the live snapshot carrying the record's artifacts (UNITY-20260929-015).

**Changes to existing checks, and only with `published_by`:**

- the record path is `publish-records/T.json`;
- the gate comes from the record instead of the task's `release_gate`;
- the loop comparing evidence to gate on `task_id`, `package`,
  `candidate_version` and `source_commit` becomes record against gate on
  all four, and evidence against record on `package` and
  `candidate_version`.

Without `published_by`, nothing changes.

## Correct layer

The PUBLISHED gate in `taskctl.py`. The publisher is unchanged: one
publication writes one record.

## Tests

`scripts/tests/test_taskctl_published_by.py` covers:

- the accepted cases: equal commit, and an ancestor commit;
- a refusal for each rule:
  - self reference, no record, sha256 mismatch, writable record, symlink;
  - record or gate `task_id` not T, conflicting own `release_gate`;
  - package mismatch, version mismatch;
  - manifest missing, manifest `task_id` not this task;
  - own commit not an ancestor, record commit missing from the repository,
    a commit that is not 40-hex;
  - an artifact missing on either side (the record has an extra binary, or
    lacks one);
- a malformed `published_by`;
- -020's free-text evidence `source_commit` passing through the manifest.

## Design Challenger

- **Round 1: REVISE.** The task's own change has to be proven to be in the published source. The loop has to be split, the hud example was wrong, the record must be read atomically, and the artifact set must match in both directions. All of this is taken above.
- **Round 2: APPROVE.** Its non-blocking notes are also taken:
  - `source_repo` must resolve to an existing git directory, and both commits must be `^[0-9a-f]{40}$` before git is called;
  - the task's `target_verification_record` may be the same file as T's;
  - the `published_by` shape is checked before any file I/O: exactly two keys, a full `UNITY-YYYYMMDD-NNN` task ID, and a 64-hex sha256. This also stops path traversal.

## Implementation and validation (2026-09-29)

- `scripts/taskctl.py`: `read_publish_record`, `covering_record` and `check_own_build`, plus the PUBLISHED call site. The changes to existing checks are the three listed above, and they apply only with `published_by`. The records directory stays fixed (`~/coordinator/publish-records`); there is no override.
- logs/02: `test_taskctl_published_by.py`, 17 tests OK. They cover both accepted cases and every refusal. The full suite runs 249 tests, OK, 1 skipped.
- logs/01 (`real-020.py`, read-only): the real UNITY-20260928-020 evidence with `published_by` = UNITY-20260927-027's record (sha256 fedfb161…). `covering_record` and `check_own_build` pass, and a wrong sha256 is refused.
- Not covered by a test: the full `taskctl transition` run of PUBLISHED. It needs a live publication; the call site is three branches read by review.
