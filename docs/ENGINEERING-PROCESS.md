# Engineering process

This document is the single policy for investigating, fixing, verifying, and
publishing a package issue. `CLAUDE.md` gives the session entry points;
`docs/TWO-AGENTS.md` and `docs/COORDINATOR.md` define the roles. The current
task board is private at `~/coordinator/TASKS.md`. `AGENTS-LOG.md` is an
append-only activity history, not the current task state. `docs/STATUS.md` is
a dated project summary, not an assignment board.

## 1. One task, one owner

Every assigned task has a permanent ID in this format:

```text
UNITY-YYYYMMDD-NNN
```

The ID is never reused, including after cancellation or discovery that the
issue is already fixed. The coordinator or May records the task and owner on
the private task board before work starts. Only that owner changes its state.
Allocate IDs in UTC date order starting at `001`; use the highest number
already allocated for that date plus one, including closed tasks.
The assignment lease is eight hours, renewed at state changes and before long
operations; expiration does not reassign a task automatically. The coordinator
may reassign it only after confirming the previous owner is idle. Do not use
peer messages as a task lock.

The allowed task states are:

```text
BACKLOG
CLAIMED
INVESTIGATING
READY_FOR_FIX
IMPLEMENTING
VERIFYING
REVIEW
READY_TO_PUBLISH
PUBLISHED
DONE
```

Side states are `ALREADY_FIXED`, `NOT_REPRODUCED`, `NOT_APPLICABLE`,
`DEFERRED`, `BLOCKED`, `REJECTED`, and `DUPLICATE`. `BLOCKED` records the
state to resume from. The other side states are closed outcomes; reopening
work gets a new task ID.

Normal transitions:

```text
BACKLOG → CLAIMED → INVESTIGATING → READY_FOR_FIX → IMPLEMENTING
         → VERIFYING → REVIEW → READY_TO_PUBLISH → PUBLISHED → DONE
```

An investigation can close as `ALREADY_FIXED`, `NOT_REPRODUCED`, `DEFERRED`,
`NOT_APPLICABLE`, `BLOCKED`, `REJECTED`, or `DUPLICATE`. During `VERIFYING`,
the physical task owner completes and records the regression test, relevant
tests, build, and live check on their assigned VM. `REVIEW` is a separate,
ephemeral Verifier subagent reading that evidence and the diff. `PASS` advances
to `READY_TO_PUBLISH`; `FAIL` returns to `IMPLEMENTING`; `INCOMPLETE` moves to
`BLOCKED` with resume state `REVIEW` until the evidence is supplied. A strictly
mechanical packaging-only change may skip independent review only under the
`NOT_APPLICABLE` exception in section 6; that path advances from `VERIFYING`
to `READY_TO_PUBLISH` after the release gate is complete. A non-package
documentation or research task may move from `VERIFYING` to `DONE`. A package
change may reach `DONE` only after `PUBLISHED`. A task is never marked done
just because the agent finished editing.

## 2. Evidence card before code

Before changing package code, create or update the task's record in
`docs/research/<task-id>-<topic>/README.md`. Use these fixed fields; write
`UNKNOWN` when a fact has not been established, and label each statement
`FACT`, `INFERENCE`, or `HYPOTHESIS` where that distinction matters.

```yaml
task_id: UNITY-YYYYMMDD-NNN
package: source-package-name
target_series: resolute
issue: LP-or-upstream-id-or-local-description
status: REPRODUCED | NOT_REPRODUCED | UNKNOWN
issue_search_result: FOUND | NOT_FOUND | UNKNOWN
source_version: exact-source-version
binary_version: exact-installed-version
source_commit: full-commit-or-UNKNOWN
observed: exact behavior and conditions
expected: exact expected behavior
reproduction: command or numbered steps
evidence: paths to logs, screenshots, test output, and boot identity
root_cause: code path and evidence, or UNKNOWN
invariant: behavior the code must preserve
existing_fix_result: one fixed value from section 3
candidate_approaches:
  - approach and measured cost
chosen_approach: exact approach or NONE
why_chosen: evidence-based reason
alternatives_rejected:
  - alternative and measured reason
code_risks:
  ownership_lifetime: checked | not_applicable | UNKNOWN
  callbacks_cancellation: checked | not_applicable | UNKNOWN
  threading_reentrancy: checked | not_applicable | UNKNOWN
  ABI_API_file_list: checked | not_applicable | UNKNOWN
unknowns:
  - unanswered checks; use [] when none
```

Do not enter `READY_FOR_FIX` until the issue is reproduced or the task is an
explicit build/packaging failure with a captured failing build, the
`existing_fix_result` is `NOT_FIXED`, and `issue_search_result` is `FOUND` or
`NOT_FOUND` with evidence. If a fix or patch already exists, verify its scope
and package state and close as `ALREADY_FIXED`, or create a new maintenance
task; do not write a duplicate patch. Record root-cause evidence and the
invariant before choosing a code change. A plausible root cause is not a
proven one.

## 3. Fixed outcomes for finding an existing fix

Search in this order and record the exact version, commit, bug, or patch found:

1. Installed package and source identity: `apt-cache policy`, `apt-cache
   showsrc`, `dpkg -S`, package metadata, and the installed system's actual
   session/component use.
2. This repository: package branches, all relevant refs and tags, patch queues,
   `docs/research/`, `docs/DECISIONS.md`, and `docs/PATCHES.md`.
3. Other work: `~/coordinator/TASKS.md`, `~/AGENTS-LOG.md`, closed/deferred task
   evidence, and records from the other builder. Check whether an equivalent
   task is active, finished, rejected, or waiting on a decision.
4. The target Ubuntu series, its updates and proposed pockets, then the current
   development series and Debian.
5. Upstream history, releases, issue tracker, and merge requests. Search by
   symptom and exact error as well as by the suspected cause.

The result must be exactly one of:

```text
FIXED_LOCAL
FIXED_IN_TARGET_UBUNTU
FIXED_IN_NEWER_UBUNTU
FIXED_IN_DEBIAN
FIXED_UPSTREAM
PATCH_ALREADY_EXISTS
NOT_FIXED
UNKNOWN
```

`NOT_FIXED` requires a dated search record covering the applicable sources.
The twenty-minute search budget in `CLAUDE.md` is a time limit, not evidence:
if the search is incomplete when time is up, record `UNKNOWN`, not
`NOT_FIXED`. `UNKNOWN` does not support a claim that no fix exists and blocks
package implementation and publication. The coordinator asks May whether to
extend the search or defer the task. `NOT_FOUND` under `issue_search_result`
means no matching issue was found in the named trackers; it does not prove no
one has reported the problem elsewhere.

When a fix exists in a newer release, record one decision:

```text
BACKPORT_PATCH
CARRY_NEWER_RELEASE
NO_CHANGE_ALREADY_FIXED
DEFER
```

If considering a newer source release, build it in the target-series chroot and
measure its build dependencies and unrelated changes. A versioned build
dependency is a claim to check against the build system, not by itself proof
that the release cannot be carried.

## 4. Implementation rules

- One task and one underlying defect per patch. Do not bundle cleanup,
  renaming, formatting, refactoring, or unrelated warning fixes.
- Keep the patch as small as the proven root cause permits. Do not add a
  defensive check at a convenient call site if the evidence places the defect
  in ownership, lifecycle, ordering, or a lower shared layer.
- Add a focused regression test when the project has a test seam. Demonstrate
  that it fails on the unmodified package, then passes with the fix. Modify an
  existing test only when the bug is in that test or the test change is
  essential to express the corrected behavior; explain that choice in the
  evidence card. If a regression test cannot be added, say why and provide the
  strongest available reproduction instead of claiming one.
- Where applicable, inspect ownership/lifetime, callback and cancellation
  paths, threading/reentrancy, error handling, and ABI/API/file-list effects.
- Run the package's relevant existing tests and a clean `sbuild` for the
  target series. Record exact commands, source commit, environment, and
  results. Do not infer ABI/API stability, file-list stability, or behavior
  outside the measured cases.
- Preserve the exact source diff and explain every changed line. Update
  `docs/PATCHES.md` for carried patches and append a decision to
  `docs/DECISIONS.md` when choosing among materially different approaches.

## 5. Independent verification

For every behavior fix, and every build fix with more than a mechanical
packaging change, a verifier other than the implementer checks the evidence and
diff. Use the `bugfix-verification` skill. The verifier does not edit the
patch. It tries to disprove the result by checking:

- the original scenario still fails on the unmodified version;
- the patched version fixes that exact scenario;
- a nearby counterexample or lifecycle path remains correct;
- the patch addresses the proven root cause and preserves the invariant;
- the diff is no broader than needed;
- relevant tests, build result, packaging contents, and stated limitations
  match the evidence.

The verifier returns exactly `PASS`, `FAIL`, or `INCOMPLETE`, with evidence,
and classifies any failure using one or more fixed finding values:

```text
FIX_INVALID
FIX_PARTIAL
TEST_INVALID
ROOT_CAUSE_UNPROVEN
PATCH_TOO_BROAD
```

`PASS` corresponds to `PATCH_CORRECT`.
Only `PASS` advances a behavior fix to `READY_TO_PUBLISH`. `INCOMPLETE` names
the missing proof; it is not a pass. Run the verifier in a separate, ephemeral
subagent context using `.claude/agents/adversarial-verifier.md`. A and B remain
focused on their own assigned tasks; do not interrupt one to review the
other's task. The implementer alone operates its assigned VM and supplies the
runtime evidence. The verifier does not edit the patch, own the task, or
operate a VM. If it cannot establish a verdict from the diff and evidence, it
returns `INCOMPLETE` and the publish gate stays closed. Do not add another
permanent team role. Skills define repeatable procedures; they do not execute
automatically or own tasks. Physical agents A and B retain their assigned
VMs, coordinator C assigns and tracks tasks, and temporary Investigator and
Verifier subagents do bounded research or read-only review without persistent
task or VM ownership.

## 6. Version and publish gates

Before building and again immediately before publishing, record the result of
the `package-version-safety` skill. The allowed results are:

```text
SAFE
UNSAFE
REPLACES_SECURITY_UPDATE
BLOCKS_FUTURE_UPDATE
UNKNOWN
```

Only `SAFE` is publishable. `UNKNOWN` stops publication until the missing
archive/version evidence is obtained. The record includes the target series,
candidate source version, versions in the target archive and update pockets,
the newest relevant release, `dpkg` version-order comparison, and the
candidate shown by `apt-cache policy` from the configured repositories.

`READY_TO_PUBLISH` requires all of the following:

```text
task_state: READY_TO_PUBLISH
source_tree: CLEAN
source_provenance: PUSHED | TRACKED_EXPORT
source_commit: PRESENT_IN_REMOTE_REF_OR_TRACKED_EXPORT
build_source_commit: EXACT_MATCH
target_series_build: PASS
version_safety: SAFE
verification_result: PASS | NOT_APPLICABLE
patch_and_decision_docs: COMPLETE
peer_notice: ACK | COORDINATOR_CONFIRMED_NO_CONFLICT
```

For a strictly mechanical packaging-only change, `verification_result` may be
`NOT_APPLICABLE` only when the evidence record states
`verification_scope: MECHANICAL_PACKAGING_ONLY` and explains why there is no
behavioral claim to verify. Use `docs/RELEASE-GATE-TEMPLATE.json` and publish
through `scripts/publish_aptly.py`; the project Bash hook blocks direct
`aptly publish` calls.

Example invocation:

```sh
python3 scripts/publish_aptly.py \
  --gate docs/research/<task-id>-<topic>/release-gate.json -- \
  aptly publish switch <distribution> [endpoint:prefix] <new-snapshot>
```

The wrapper checks the structured gate, that the gate and each evidence file
are tracked, committed, and clean, the clean source tree, exact build commit,
and pushed remote-tracking ref (or tracked export) before starting aptly.
Refresh the named remote-tracking ref after pushing; the wrapper does not fetch
from the network. It cannot prove a fact merely because a JSON field says
`PASS`; the evidence content and post-publication checks remain required.

Before publication, append a `START` entry to `AGENTS-LOG.md`, state the
package and full candidate version, and notify the other package owner. If
direct messaging fails, append to that agent's inbox and wait for its
acknowledgement; a failed send is not an acknowledgement. If the other agent
is confirmed idle, the coordinator may record
`COORDINATOR_CONFIRMED_NO_CONFLICT`.

After publication, verify that aptly contains the exact source and binary
versions. On the assigned clean target, use the repository's normal upgrade
path and verify `apt-cache policy` and the installed package version. A manual
`dpkg -i` experiment is useful evidence but does not satisfy this gate. Record
the test, repository version, target state, and limitations before marking
`PUBLISHED`; mark `DONE` only after all records are committed and pushed.

## 7. Canonical fix examples

Promote only independently verified fixes as examples. Copy
`docs/FIX-EXAMPLE-TEMPLATE.md` into the relevant research record or example
collection. An example is not canonical until it names its source commit,
review result, passing evidence, and known limits. Keep `Why this
implementation` and `Why not these alternatives` explicit so a working but
architecturally misplaced patch is not taught as the preferred solution.

## 8. Policy, live state, and knowledge

- **Policy:** `CLAUDE.md`, this process, `TWO-AGENTS.md`, and `COORDINATOR.md`.
- **Live task state:** private `~/coordinator/TASKS.md`, maintained by the
  coordinator or May. It is the sole authority for task owner and state.
- **Activity history:** `~/AGENTS-LOG.md`, append-only; never treat its last
  `START` as current without checking for a later `DONE`.
- **Knowledge:** `docs/research/`, `docs/DECISIONS.md`, `docs/PATCHES.md`, and
  canonical examples in the repository.
- **Session state:** `docs/status/A.md` and `docs/status/B.md` record each
  assigned desktop and work-in-progress details. They do not assign tasks.
- **Project summary:** `docs/STATUS.md` is dated and maintained by the
  coordinator; it is not the live task board.

Keep private coordination notes, credentials, and correspondent drafts out of
the public repository. If a credential was committed, removing it from the
current file does not remove it from Git history; rotate it and follow the
repository owner's history-removal process separately.

## 9. Shell command guard

The project `.claude/settings.json` installs a `PreToolUse` guard for Claude
Code's `Bash` tool. It blocks common direct forms of broad staging, force-push,
`aptly publish`, `xwd`, `pkill`/`pgrep -f`, globbed `rm -rf`, and `rm -rf`
with an unguarded shell variable. This is a narrow command-pattern guard, not a
shell security boundary: aliases, wrappers, alternate binaries, and equivalent
commands may bypass it. It does not validate package correctness.

Claude Code `PreToolUse` hooks can also match MCP tools, but this project
currently has no VBox MCP hook. Until one is implemented and checked against
the actual VBox tool names and input schema, VM restores remain governed by the
manual ownership and restore gate in `docs/TWO-AGENTS.md`. Do not describe the
current Bash hook as protection for VBox MCP operations.
