# UNITY-20260928-005: taskctl's path to DONE for non-package tasks

From UNITY-20260927-046 and UNITY-20260928-007. Agent A, 2026-09-28.

## Evidence card

```yaml
task_id: UNITY-20260928-005
package: infra (scripts/taskctl.py, docs/ENGINEERING-PROCESS.md section 1)
target_series: not_applicable
issue: >-
  taskctl.py has no honest path to DONE for non-package tasks: a tool change
  that passed the Verifier cannot leave REVIEW, provisioning work has to fill
  defect fields to pass READY_FOR_FIX, and a tool change can reach DONE with
  no Verifier at all
status: REPRODUCED
issue_search_result: FOUND   # local records: ~/coordinator/evidence/UNITY-20260927-046.json and UNITY-20260928-003.json "note" fields say their READY_FOR_FIX/IMPLEMENTING/VERIFYING were recorded after the work; UNITY-20260928-007 is in REVIEW (runs/open-tasks.txt)
source_version: scripts/taskctl.py at origin/main 629cb20
binary_version: not_applicable
source_commit: branch a/UNITY-20260928-005 from origin/main 629cb20
observed: >-
  runs/reproduction-before.txt, temporary boards (TASKCTL_BOARD), taskctl at
  629cb20:
  1. a non-package task in REVIEW with verification_result=PASS and
     terminal_evidence: "transition REVIEW -> DONE is not allowed";
  2. a provisioning task (create repositories) with a plan: INVESTIGATING ->
     IMPLEMENTING "is not allowed", and READY_FOR_FIX "requires evidence
     fields: reproduction, reproduction_result, existing_fix_result,
     issue_search_result, root_cause, invariant, chosen_approach";
  3. a tool-code task in VERIFYING with package_change=false, a
     validation_record and no verifier record at all: -> DONE succeeds (rc 0).
expected: >-
  package tasks reach DONE only through PUBLISHED (unchanged); a tool change
  reaches DONE only after the Verifier's PASS, without READY_TO_PUBLISH or
  PUBLISHED; documentation/research and operational work reach DONE after
  their validation without inventing defect fields
reproduction: tools/reproduce.sh (temporary board and fixture evidence files; output runs/reproduction-before.txt)
reproduction_result: PASS
root_cause: >-
  taskctl knows only one distinction, the boolean package_change, and uses
  it in two places: VERIFYING -> DONE is allowed when it is false (meant for
  documentation, ENGINEERING-PROCESS section 1), and DONE is refused when it
  is true. The transition table has no REVIEW -> DONE, and READY_FOR_FIX
  requires the defect card of section 2 for every task. So (1) a non-package
  change that is reviewed has no exit, (2) non-defect work must fill defect
  fields, and (3) "not a package" is taken to mean "documentation", letting
  tool code - which section 5 puts under independent verification for every
  behaviour fix - skip the Verifier.
invariant: >-
  every task reaches DONE through the gates of its kind: package - PUBLISHED;
  tool (code that changes behaviour, e.g. scripts/*.py) - Verifier PASS;
  documentation/research - its validation record; operation (acts on
  infrastructure: repositories, VMs, archive state) - its validation record
  and the recorded authorization. No kind needs a field that does not apply.
existing_fix_result: NOT_FIXED   # local tool
candidate_approaches:
  - "K1 (amended after Design Challenger review 1) - an explicit task_kind:
    package | tool | operation | documentation. Mixed task: the highest of
    package > tool > operation > documentation.
    Kind resolution: task_kind if given; if absent and package_change is true,
    package (legacy tasks keep their path); otherwise, from READY_FOR_FIX on,
    refused. package_change, when given, must be a bool and agree (true <=>
    package). Package markers in the evidence (build_manifest, release_gate,
    candidate_version, version_safety) force package: any other kind is
    refused.
    Kind lock: at the first transition that resolves a kind (READY_FOR_FIX, or
    any later one for legacy tasks) taskctl writes <evidence dir>/<id>.kind
    (the evidence dir next to the board); every later transition must resolve
    to the same kind, whatever --evidence file is given.
    READY_FOR_FIX: package and tool - the section 2 defect card, as today;
    operation - scope, chosen_approach, existing_state_check (what is already
    there - the operation's counterpart of existing_fix_result) and a
    structured authorization {approved_by: May|C, reference: an existing file
    path or a PENDING-MAY entry, scope}; documentation - scope and
    chosen_approach. All kinds keep architectural_task,
    design_challenger_required and correct_layer (and design_review_result
    APPROVE when required).
    VERIFYING: package - regression_test + build_manifest (as today); tool -
    regression_test + validation_record; operation and documentation -
    validation_record.
    DONE: package - only from PUBLISHED; tool - only from REVIEW, re-checking
    verification_result=PASS and review_status; operation and documentation -
    from VERIFYING, or from REVIEW with PASS. Transition table: REVIEW -> DONE
    added, gated by kind. BLOCKED cannot resume into DONE (unchanged)."
  - "K2: only add REVIEW -> DONE for package_change=false with PASS. Fixes (1)
    but not (2) or (3)."
  - "K3: new states for non-package work (e.g. PLANNED, APPLIED). Not built."
  - "Tool NOT_APPLICABLE verifier for mechanical edits (like section 6):
    not added - no evidence of a mechanical tool edit being blocked."
chosen_approach: K1 as amended
why_chosen: >-
  It names what the process already distinguishes in prose (section 1:
  documentation/research may go VERIFYING -> DONE; section 5: every behaviour
  fix gets a Verifier; section 6: packages publish) and makes taskctl enforce
  it with the existing states. The lock and the package markers close the
  ways a package task could claim another kind. INFERENCE: 046 and 003 would
  have been operation, 007 tool, this task tool.
alternatives_rejected:
  - "K2: leaves the fabricated READY_FOR_FIX fields for operations and the
    Verifier-less DONE for tool code (reproduced as 2 and 3)."
  - "K3: more states to learn and to migrate the board to, for what an
    evidence field can express. INFERENCE - not built."
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: checked - taskctl locks the board (fcntl) around each transition; unchanged
  ABI_API_file_list: >-
    evidence JSON gains task_kind (and authorization / existing_state_check
    for operations); taskctl writes <id>.kind lock files next to the evidence;
    section 1 defines READY_FOR_FIX as "approach recorded, ready to implement"
    and section 2's "do not enter READY_FOR_FIX until reproduced" applies to
    package and tool tasks
unknowns: []
migration: >-
  Open tasks (runs/open-tasks.txt): package_change true without a kind
  (021, 023, 037, 041, 052) resolve to package - unaffected. 026 (B,
  INVESTIGATING, package_change false) sets task_kind before its
  READY_FOR_FIX. 047 (B, BLOCKED, false) sets task_kind=operation with
  authorization; its resume_state must still validate. 007 (A, REVIEW, false)
  sets task_kind=tool and closes REVIEW -> DONE on its recorded PASS. 057 and
  this task set a kind before READY_FOR_FIX.
design_challenger_required: true
design_review_result: APPROVE
architectural_task: true
correct_layer: >-
  taskctl.py is the only supported writer of the board and enforces the
  transition graph and evidence (section 1); the rule has to be there and in
  section 1, which it implements.
defensive_workaround_rejected: >-
  Closing such tasks through BLOCKED, or recording READY_FOR_FIX after the
  fact (what 046 and 003 had to do), keeps the board valid only by making its
  history untrue.
```

## Test plan

New `scripts/tests/test_taskctl.py` on temporary boards (TASKCTL_BOARD) and
fixture evidence:

- each kind x each DONE path, allowed and refused; package via REVIEW -> DONE
  and VERIFYING -> DONE refused; tool via VERIFYING -> DONE refused, via
  REVIEW -> DONE with FAIL or INCOMPLETE refused, with PASS allowed;
- kind changed between transitions, and an alternate --evidence file with
  another kind, refused (the lock);
- task_kind / package_change missing, non-bool and mismatched;
- package markers with a non-package kind refused;
- operation READY_FOR_FIX without authorization or with a placeholder one
  refused; documentation and operation READY_FOR_FIX without defect fields
  allowed;
- BLOCKED resumed into REVIEW, then DONE gated by kind;
- legacy evidence (package_change true, no kind) still reaching
  PUBLISHED -> DONE, and refused on REVIEW -> DONE;
- existing scripts/tests stay green (test_version_safety imports taskctl);
- tools/reproduce.sh against the fixed taskctl: case 1 allowed with
  task_kind=tool, cases 2 and 3 as the kinds define.

## Design review

1. **REVISE** (2026-09-28): layer and distinction right; K1 had to close the
   publish-path leaks (kind changeable via another evidence file, package
   markers, fail-safe for a missing kind, DONE checked by kind and source
   state), make authorization structured, keep the design fields for all
   kinds, add the operation's existing-state check, define the kind order,
   and fix the card's evidence (reproduction script and fixtures, the open
   task query, citations for 046/003). Addressed above.
2. **APPROVE** (2026-09-28, same reviewer), with one condition taken into the
   implementation and tests: at deployment every open task gets its
   `<id>.kind` lock at once (tools/seed-kind-locks.py, run by the
   coordinator at merge), because until a task's first transition under the
   new code a legacy package task without markers (052; 021 and 041 carry
   only candidate_version) could otherwise be relabelled by editing its
   evidence. Known limit accepted: the lock sits in a directory agents can
   write, so it detects a relabel rather than preventing one - the same
   trust level as the evidence JSON.

