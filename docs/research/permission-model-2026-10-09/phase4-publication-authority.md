# Phase 4 - routine publication authority (design; Design Challenger APPROVE at round 5, 2026-10-09)

Kind: `tool`. Implemented by the architecture session. Depends on nothing in
code; phase 0 only records the decision.

## Problem

Today the publication is tool-checked but not tool-authorised: the owner
runs `scripts/publish_aptly.py --gate` after C's check and May's chat
confirmation, and the script reads neither. May decided (2026-10-09, item 2)
that C's GO replaces his confirmation for routine releases and that the
authorization must be bound to the task, the branch, the source commit, the
gate and the publication artifacts.

## Invariant

`publish_aptly.py` switches the live publication only when a single-use
approval record exists that C wrote for exactly this gate: same task, same
gate bytes, the repository HEAD equal to the approved gate commit and present
in the named task branch on `origin`, same source commit and tree, same
snapshot/distribution/prefix, same artifact list and hashes, inside its
validity window. A first publication of a source package needs May's
reference in the record. Nothing else about the publisher changes.

## Design

### The approval record

`~/coordinator/publication-approvals/<task_id>.json`, mode 0600, written
atomically by `scripts/taskctl.py approve-publication`:

```json
{
  "schema": 1,
  "kind": "publication-approval",
  "task_id": "UNITY-YYYYMMDD-NNN",
  "approved_by": "C",
  "approved_at": "2026-10-09T08:00:00Z",
  "not_after": "2026-10-09T12:00:00Z",
  "branch": "a/UNITY-YYYYMMDD-NNN",
  "gate_file": "docs/research/<task>/gate/release-gate.json",
  "gate_sha256": "...",
  "gate_commit": "<HEAD of the task worktree that holds the gate>",
  "package": "...", "candidate_version": "...",
  "source_repo": "packages/<pkg>", "source_commit": "...", "source_tree_hash": "...",
  "snapshot": "...", "distribution": "resolute", "prefix": ".",
  "build_manifest_sha256": "...", "evidence_manifest_sha256": "...",
  "artifacts": [{"file": "...", "sha256": "...", "kind": "binary"}],
  "known_gaps": ["UNITY-..."],
  "first_publication": false,
  "may_reference": ""
}
```

`approve-publication TASK --actor C --repo <task worktree> --branch <name>
[--gaps ID,...] [--may-reference TEXT]` refuses unless all of these hold:

- actor is `C` (the board's rule for assignment and release is reused);
- the board row is `READY_TO_PUBLISH` and its evidence names the gate;
- `<repo>/<gate_file>` is tracked, committed and clean; its sha256 is
  recorded; the repository HEAD is the `gate_commit`;
- `git -C <repo> branch -r --contains <gate_commit>` lists `origin/<branch>`
  (the branch is pushed and holds the gate);
- the gate is schema 1, `task_state: READY_TO_PUBLISH`, and the build
  manifest at the gate's path has the gate's sha256; the artifact list is
  copied from the manifest, not typed;
- **the publication tools of the task worktree are current** (round 3
  finding 1, round 4 finding 1): the git blob ids of the six scripts the
  publisher executes or imports from the task worktree -
  `scripts/publish_aptly.py`, `scripts/approval_record.py`,
  `scripts/tested_build.py`, `scripts/build_dependencies.py`,
  `scripts/version_safety.py` and `scripts/apt_view.py` (the last two
  decide the SAFE verdict) - plus `scripts/taskctl.py`, which the owner
  runs from the same worktree for `READY_TO_PUBLISH` and `PUBLISHED`
  (round 5 remark: over-inclusion, deliberately), at
  `gate_commit` equal those at the local `origin/main` ref. The comparison
  is against the local remote-tracking ref (round 4 finding 2): the caller
  fetches beforehand with plain `git fetch`, which the guard allows;
  taskctl's `git_out` runs with `protocol.allow=never` and must not fetch.
  A task branch forked before this phase therefore cannot be approved until
  `origin/main` is merged into it (section 10 allows that merge; nothing is
  rebased); the publisher makes the same check, plus `git status
  --porcelain -- scripts/<the seven>` empty (round 4 remark), and refuses
  with "publication tools are older than main or modified: merge
  origin/main into the task branch; regenerate the gate only if the merge
  touched a pinned file". A task that changes a publication tool never
  also publishes a package (May's "never combine" rule): otherwise it could
  neither be approved nor merged first (round 4 finding 4);
- an unexpired approval with the same `gate_sha256` is refused as already
  present; one with another `gate_sha256` (the gate was regenerated) is
  replaced and the replacement is logged. `approve` and `revoke` take the
  publisher's lock `publish-records/<task>.lock` with `LOCK_NB` and refuse
  with "publication in progress" when it is held, so the file cannot
  change under a running publisher and a running publication never blocks
  the board lock that every taskctl command holds (round 1 finding 4,
  round 2 finding 5). Their git calls go through taskctl's `git_out`
  watchdog. `~/coordinator/publication-approvals/` and `used/` are created
  with mode 0700;
- `first_publication` is computed, not typed (round 1 finding 1, round 2
  finding 2): the set S of known sources is the `Source:` (a ` (version)`
  suffix stripped) or else `Package:` of every stanza in
  `/srv/aptly/public/<prefix>/dists/<distribution>/main/binary-amd64/Packages`
  (a file read, never `aptly publish`; 39 names on 2026-10-09). Publish
  records are not consulted. `first_publication` is `package not in S`.
  The publisher recomputes it. When true, `--may-reference` is required
  (decision 4: a new package is never routine); it is free text naming
  where May said GO, UTF-8 allowed, control characters refused (finding 9).
  A package that was removed from the live publication (a section 6a
  operation) is therefore new again and needs May's reference.
- `not_after` = `approved_at` + 4 h, the same window as the gate-time
  version check; the publisher also refuses an `approved_at` more than
  5 minutes in the future (finding 5).
- `may_reference` is `""` when absent, never `null`. The record is read with
  a strict reader in a new `scripts/approval_record.py` (regular file, owner
  uid, mode 0600, UTF-8 JSON without control characters, exact key set, no
  null, `task_id` equal to the file name's task, window and future-date
  checks), shared by taskctl and the publisher; the guard's `_strict_json`
  is not imported (finding 6). A second reader, `read_used(path)`, accepts
  the same keys plus `outcome` and `consumed_at` and skips the window
  checks (round 2 finding 1).

The command appends one line to `~/AGENTS-LOG.md`: `C APPROVE publication
<task> <package> <version> gate <sha256[:12]> branch <name>`.

`revoke-publication TASK --actor C` deletes the record and logs it.

### The publisher

In `publish_aptly.py main()`, after the gate and board checks and before the
snapshot content check:

1. Read `~/coordinator/publication-approvals/<task>.json` with
   `approval_record.read()`. Missing: `fail("no publication approval by C;
   run taskctl.py approve-publication")`.
2. Refuse unless: `approved_by == "C"`, `now < not_after`, `approved_at`
   not in the future, the repository HEAD equals `gate_commit` (finding 2:
   any commit after the approval, including one to `scripts/publish_aptly.py`
   itself, needs a new approval), `task_id`, `package`,
   `candidate_version`, `source_commit`, `source_tree_hash`, `snapshot`,
   `distribution`, `prefix` equal the gate; `gate_sha256 == sha256(gate_path)`
   and `gate_file` equals the gate's repository-relative path;
   `origin/<branch>` is among `git branch -r --contains HEAD`;
   `build_manifest_sha256` and `evidence_manifest_sha256` equal the gate's;
   the artifact list equals the manifest's `(file, sha256)` set;
   `first_publication` recomputed is false, or `may_reference` is non-empty.
3. Consumption happens before aptly runs (round 1 finding 3, round 2
   findings 1 and 4): right after the `START` log line the approval bytes
   validated in step 1 are re-hashed against the file, the record is
   written to `~/coordinator/publication-approvals/used/<task>-<stamp>.json`
   with `outcome: "started"` and `consumed_at`, and the original is
   unlinked. If that consume step fails, the publisher stops **before**
   aptly runs (`FAIL(approval)` in the log). The outcome is then rewritten
   on every path that exists in `main()` today:
   - `aptly` could not start (OSError): `failed(start)`;
   - the switch returned non-zero: `failed(aptly rc N)`;
   - the `publish show` check failed: `failed(post-publication check)`;
     aptly may have switched, recovery is manual as today;
   - the switch and the check passed: `published`, written before the
     publish record. If the write-once record then cannot be written, the
     approval is already consumed and the message "do not rerun blindly"
     stands: recovery is manual.
   The sha256 recorded in the publish record and checked by taskctl is the
   sha256 of the `used/` file **after** `outcome: published` was written;
   the file is not modified afterwards. A failed or interrupted switch
   therefore needs a fresh approval from C, who supervises the run.
   Order of the consume step: re-hash the original through `O_NOFOLLOW`,
   write `used/<task>-<stamp>.json` with `O_EXCL` and fsync, unlink the
   original. If the unlink fails after the write, the original and an
   orphan `used/...` with `outcome: started` remain; the next run consumes
   again under the publisher's lock, and the write-once record blocks a
   repeat publication. `read_used` reads only the file the publish record
   names, so an orphan is never consulted (round 3 finding 4).
4. The publish record keeps `schema: 1` (round 2 finding 3: schema 2 would
   break every reader and cannot be rolled back on 0444 write-once files)
   and gains `"authorization": {"file": "used/<task>-<stamp>.json",
   "sha256": ..., "approved_by": "C", "approved_at": ...,
   "first_publication": ..., "may_reference": ...}`. No reader checks the
   key set, so older tools ignore the key.

`taskctl.py` `PUBLISHED` (all three record paths: direct, `published_by`,
`released_in`; round 1 finding 7): a record whose `published_at` is later
than the constant `AUTHORIZATION_REQUIRED_SINCE` (set to the merge time of
this phase) must carry `authorization` with `approved_by: "C"`, and the
`used/` file it names must exist, read with `read_used`, with the recorded
sha256 and `outcome: published`. Records from before that time are accepted
as today, so a task published before the merge still closes. Rollback is a
revert of the scripts; records are untouched.

C's final record (decision 2, round 2 finding 8, round 3 finding 5): the
write-once publish record is the publisher's; C writes nothing at the end
of the run. C's record of the publication is the `used/` approval with
`outcome: published` (C's authorization and its result, written by the
publisher) and C's merge of the task branch into `main` per section 10,
which carries the publication records. The process text says this plainly.
No new duty is added to C.

### Process text

- ENGINEERING-PROCESS section 6, step 10: "C checks the gate and records the
  approval with `taskctl.py approve-publication`. The owner then runs
  `scripts/publish_aptly.py --gate <gate>`. May's confirmation is needed
  only for a first publication of a source package (the approval carries
  his reference) and for the exceptional operations of section 6a. A
  refusal returns to step 8 and needs a new approval." Step 8: "before C's
  approval is asked" replaces "before May is asked" (finding 8). The
  example block's comment "after C's check and May's confirmation" becomes
  "after C's approve-publication" (round 2 finding 6). The 40-binary and
  maintainer-script limits of decision 4 are the signer's (phase 5), not
  this record's. New process line in step 1 (slot): "before the gate, merge
  `origin/main` into the task branch (section 10 permits the merge, never a
  rebase) so that the publication tools are current; `approve-publication`
  and the publisher refuse otherwise. A task that changes a publication
  tool never also publishes a package" (round 3 finding 1, round 5
  remark).
- The `first_publication` rule reads `main/binary-amd64/Packages` because
  the live `Release` lists `Components: main` and `Architectures: amd64`
  only; the command reads `Release` and refuses if either list differs, so
  the assumption is checked, not hard-coded (round 3 remark).
- Section 6a (new, short): exceptional operations keep May's separate GO:
  rollback (C prepares the plan, the Verifier checks the expected result,
  May gives the GO; nothing automated), removal of a package, the first live
  migration to the signer, key operations, trust-policy changes.
- Section 5: the existing `REVIEWED` / `INDEPENDENTLY_REPRODUCED` rule is
  kept unchanged (finding 8); only the first-publication requirements are
  added: Design Challenger on the packaging, `INDEPENDENTLY_REPRODUCED`,
  May's reference in the approval.
- TWO-AGENTS "Ours" bullet: unchanged (publishing to our aptly stays
  "ours"; the GO is C's).
- COORDINATOR.md: one bullet, "Records the publication approval after
  checking the gate; the approval is single-use and bound to the gate."

### Upstream Liaison

Moved out of this phase (finding 9: it is decision 7, not decision 2). It
becomes its own small docs task after phase 4, with the explicit statement
that the subagent sends nothing (Bash `curl` can POST) and does
correspondence and tracker research only.

## What this phase does not do

- No change to the guard, the hook or `~/.claude/settings.json`.
- No change to what `publish_aptly.py` publishes or how (switch to the
  gated snapshot only). No rollback automation (May, decision 5).
- The approval is forgeable by any session of user `claude`; it is a
  workflow record, not authentication. The signer (phase 5) is the
  boundary.
- C's duties do not change: C already checks the gate before every
  publication; the command records that check in a form the tools read.

## Tests

- `scripts/tests/test_taskctl_approve.py` (new, fixtures under a temp HOME
  and a temp git repository with a fake `origin`): refusals for actor
  A/B/May, wrong board state, gate not tracked or dirty, gate commit not in
  `origin/<branch>`, manifest hash mismatch, first publication without
  `--may-reference`; re-approval with the same sha refused, with another
  sha replaced and logged; the positive case writes the record with the
  manifest's artifacts and mode 0600.
- The end-to-end harness of `test_build_dependencies_consumers.py` (fake
  HOME, local remote, fake `aptly` first on PATH, `publish_aptly.py
  --gate`) is extracted to `scripts/tests/publish_harness.py` and reused
  (round 2 finding 7); the following run through it, not as pure-function
  tests: no approval; expired; `approved_at` in the future; another gate
  sha; another branch; `HEAD != gate_commit`; another artifact set;
  `first_publication` without reference; approval saved under another
  task's file name; approval present only in `used/`; mode 0644 or a
  symlink; the positive case moves the file to `used/` with
  `outcome: published` and writes `authorization`; a failed switch leaves
  `outcome: failed` and no valid approval.
- `taskctl` `PUBLISHED`, on all three paths (direct, `published_by`,
  `released_in`): refuses a record dated at or after
  `AUTHORIZATION_REQUIRED_SINCE` without `authorization`, with a missing or
  differing `used/` file, or with an outcome other than `published`;
  accepts a record dated before it (round 3 finding 2).
- `approve-publication` and the publisher refuse a worktree whose
  publication-tool blobs differ from `origin/main` (round 3 finding 1),
  and the publisher refuses one of those scripts modified in the working
  tree (round 4 remark); the positive case runs after merging main into
  the test branch.
- `git_out` reuse: its error message takes a caller-supplied prefix so
  approve/revoke do not report "released_in:" (round 3 remark).
- Full suite stays green.

## Acceptance (in new sessions)

- C session: `approve-publication` works for `--actor C` on a real gate and
  is refused for `--actor A`.
- Owner session: `publish_aptly.py` refuses without the approval and
  succeeds with it on the first routine publication after the merge (an
  established package), with the db backup of step 3 taken first; the
  publish record shows `authorization`; `PUBLISHED` passes.
- A first publication of a new package after the merge is refused without
  `--may-reference`.

## Rollback

Revert the scripts and the documents to the merge base; an approval file
left behind is ignored by the old publisher; publish records keep schema 1
and need no change.

## Design review round 1 (2026-10-09): REVISE, all ten findings taken

1 first_publication from the live Packages and the records; 2 HEAD must
equal gate_commit; 3 consume before aptly runs, with an outcome; 4 the
publisher's lock in approve/revoke; 5 future-dated approvals, idempotent
re-approval; 6 own strict reader, `""` not `null`; 7 schema 2 and the three
record paths; 8 process text (step 8 wording, 6a, section 5 kept);
9 Upstream Liaison moved to its own task; 10 the extra tests.

## Design review round 2 (2026-10-09): REVISE, nine findings taken

1 the hashed bytes are the used/ file after outcome: published, read with read_used; 2 first_publication from the live Packages only, removal makes a package new again; 3 publish records keep schema 1, authorization required by published_at; 4 every failure path after START named with its outcome, consume failure stops before aptly; 5 LOCK_NB and git_out in approve/revoke; 6 the example comment in section 6; 7 the end-to-end harness extracted and reused; 8 C's final record named; 9 UTF-8 reference without control characters. Non-blocking: directory mode 0700, decision-4 limits are phase 5.

## Design review round 3 (2026-10-09): REVISE, taken

1 (blocking) in-flight task branches carry the old publisher: approve and the publisher require the publication-tool blobs of gate_commit to equal origin/main, and step 1 says to merge origin/main into the task branch before the gate; 2 tests wording aligned to the published_at rule on all three paths; 3 existing records (24, 2026-09-29T16:10:23Z .. 2026-10-09T05:40:24Z) all before SINCE - no misfire; 4 consume ordering and the orphan case stated; 5 C writes nothing at run end - said plainly. Remarks taken: Release-checked component/arch, neutral git_out prefix. Prototype mismatches P1-P4 are implementation items (UTF-8 without control characters, read_used with lstat checks, O_NOFOLLOW and fsync in consume, 40-hex commits, typed known_gaps).

## Design review round 4 (2026-10-09): REVISE, taken

1 (blocking) `version_safety.py` and `apt_view.py` added to the compared tools (seven in all); 2 the comparison is against the local `origin/main` ref, the caller fetches, `git_out` never fetches; 3 merge of main into a task branch confirmed consistent with section 10 and the gate's clean-tree check; 4 a tool-changing task never publishes a package (stated); 5-6 confirmed. Remarks taken: the publisher also requires the seven scripts unmodified in the working tree; the refusal text says when the gate must be regenerated.

## Design review round 5 (2026-10-09): APPROVE

Remarks taken: the compared set is the six scripts the publisher executes or imports plus taskctl.py (over-inclusion); the never-combine line is in the process text; heading corrected; the modified-working-tree refusal is in the tests.

## Implementation (branch `arch/permission-model-phase4`)

- `scripts/approval_record.py` (new): the record's strict reader (`read`,
  `read_used`), writer, `consume`, `set_outcome`, `remove`, and
  `known_sources` (the live `Packages` index behind a `Release` check);
  `PUBLICATION_TOOLS` lists the seven compared scripts.
- `scripts/taskctl.py`: `approve-publication` and `revoke-publication`
  (actor C, board state, gate tracked and clean, HEAD in `origin/<branch>`,
  tool blobs equal `origin/main`, manifests pinned, artifacts copied,
  first publication from the live index, replace-or-refuse, the publisher's
  lock with `LOCK_NB`, a log line); `check_record_authorization` for
  `PUBLISHED` on all three record paths, gated by
  `AUTHORIZATION_REQUIRED_SINCE`; `git_out` takes a message prefix.
- `scripts/publish_aptly.py`: `check_approval_early` right after the board
  checks (record, HEAD, branch, tools, gate bytes and fields),
  `check_approval_artifacts` once the manifest is validated (artifact set,
  first publication), `consume_and_switch` (consume before aptly, outcome
  on every failure path, `published` before the record), the record's
  `authorization` field (schema stays 1); `LIVE_PUBLIC` for the index.
- `scripts/tests/publish_harness.py` (extracted from
  `test_build_dependencies_consumers.py`, which now subclasses it): a fake
  live publication, `write_gate` with a committed evidence manifest,
  `approve`, `publish(approved=...)`.
- Process text: ENGINEERING-PROCESS section 5 (first publication), section
  6 steps 1, 8, 10, 12 and the example comment, new section 6a;
  COORDINATOR.md one bullet.
- Not in this phase: the Upstream Liaison definition (its own small docs
  task); any change to the guard, the hook or the settings.

`AUTHORIZATION_REQUIRED_SINCE` in `taskctl.py` is set to the merge time of
this phase when it is merged; every existing publish record (24, the latest
2026-10-09T05:40:24Z) is earlier, every record the new publisher writes is
later.

## Verification (2026-10-09)

Independent Verifier (ephemeral subagent, REVIEWED; it ran the full suite in the worktree: 455 tests OK, 1 skipped, and probed `check_approval_artifacts` with its own fixtures): **PASS**, with one FIX_PARTIAL on the tests: the publisher's part-2 check and several publisher-side refusals (expired, future-dated, another branch, another task's file name, a used-only copy, a symlink, a changed manifest hash) rested on review only. Taken before the merge: `PublisherSideRefusalsTest` (8 cases through the real publisher) and `ArtifactsAndFirstPublicationCheckTest` (5 cases on the function); a gate without `publish.distribution` is now a refusal instead of a traceback; step 10 says what happens when the outcome write fails (`PUBLISHED` refuses, manual recovery). Remarks noted: the validity window is checked at the early check only; `AUTHORIZATION_REQUIRED_SINCE` is set to the merge time in the merge preparation commit. Counterexamples tried by the Verifier and refused by the code: revoke or re-approve during a run (the publisher holds the lock), a rewrite between read and consume (byte compare), a `used/` path escape, a gate without prefix.
