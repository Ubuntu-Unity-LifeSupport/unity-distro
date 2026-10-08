# UNITY-20260929-009: publication sequence in ENGINEERING-PROCESS section 6

Task kind: docs. Owner: A. Parent: UNITY-20260927-021.

## 1. Problem

Section 6 of `docs/ENGINEERING-PROCESS.md` describes the gate and the
publisher, but it has gaps:

- It has no step that adds the build to the repository `unity-resolute`
  and creates the gated snapshot `unity-resolute-YYYYMMDD-NNN`.
- Its example passes `--prefix unity`. The live publication is at
  prefix `.`, which is in every publish record in
  `~/coordinator/publish-records/` and in `dists/resolute` at the root of
  `/srv/aptly/public`.
- With `--prefix unity`, a gate would be created, but the switch would
  name a publication that does not exist.

The coordinator widened the task to the publication lessons of
2026-09-29 to 2026-10-08. Each lesson is a short rule:

- the repository and snapshot steps, the snapshot name, and `-r2` on
  replacement;
- `source_repo` only under the publishing task's worktree;
- a peer notice before the gate;
- `taskctl` from the task worktree;
- prefix `.`;
- nothing edited after the gate;
- `published_by`;
- replacing unpublished records;
- `buildinfo_identical`;
- a target check without drop-ins and with a natural boot;
- known gaps before the gate;
- security material kept out of public branches.

## 2. Where each rule is enforced

A research subagent read the code, and the Design Challenger re-checked
it. Each rule in the new text is marked **[tool]** or **[process]**.

| Rule | Status |
|---|---|
| `packages/<source>` | **[tool]**: `create_release_gate.py:74-76`, `publish_aptly.py:327-329` |
| `peer_notice` values | **[tool]**: `create_release_gate.py:57-58`, `publish_aptly.py:300-301`. Not checked by `taskctl` |
| Gate path inside the repository the script lives in | **[tool]**: `taskctl.py:569-572, 455, 477-484`, `publish_aptly.py:252-254` |
| Evidence files pinned by hash | **[tool]**: `create_release_gate.py:96-121, 138-140`, `publish_aptly.py:357, 387, 398, 416-417` |
| Board state at gate creation | **[tool]**: `create_release_gate.py:80` |
| `published_by` | **[tool]**: `taskctl.py:285-305, 319-321, 337-362`, comparing artifact names, not bytes |
| `tested_build` modes | **[tool]**: `tested_build.py:38, 157-199` |
| Source package bytes in the snapshot | **[tool]**: `publish_aptly.py:172-180, 455-458` |
| Binaries in the snapshot | Matched by name, version and architecture only (`publish_aptly.py:452`) |
| Repository name, snapshot name, diff, db backup, known gaps, security branches, natural boot | **[process]** |

The guard admits aptly's `repo` and `snapshot` subcommands
(`command_guard.py:408, 538`) and refuses `publish`.

There is no canonical db backup script. The six copies under
`docs/research/*/tools/backup-db.py` have all diverged.

## 3. Change

In `docs/ENGINEERING-PROCESS.md` section 6, the following old text is
replaced by a numbered publication sequence of 12 steps, the rules B, P,
K and S, and a corrected example:

- the old example workflow;
- the publisher paragraph;
- the `START` and peer notice paragraph;
- the after-publication paragraph.

Every requirement of the removed paragraphs is kept in the new steps:

- the publisher's list of pushed and clean files;
- the inbox fallback for a failed send;
- `COORDINATOR_CONFIRMED_NO_CONFLICT` only for a peer confirmed idle;
- the package and version in the `START` line;
- the check of the exact published versions;
- the assigned clean target and the contents of its record;
- `dpkg -i` does not satisfy the gate;
- `DONE` only after the records are pushed.

There is one narrow exception to the `dpkg -i` rule, and it needs C's
approval: debs from the published repository whose hashes match the
gated manifest, as in UNITY-20261002-003.

## 4. Design review

The Design Challenger reviewed the text as follows.

- **Round 1: REVISE**, with these required changes:
  - the snapshot comparison covers only the source package; the pool
    sha256 check is a **[process]** step;
  - the restored requirements;
  - the `dpkg -i` exception made narrower;
  - `published_by` compares artifact names;
  - the `buildinfo_identical` byte comparison is **[process]**.
- **Round 2: APPROVE.** Change made after the approval: step 8 now says
  that a decision record is pinned only when the task requires one. The
  Verifier should also check how the nested lists in step 11 render.

## 5. Results

To be filled after the review and verification.
