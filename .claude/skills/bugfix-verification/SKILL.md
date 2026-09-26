---
name: bugfix-verification
description: Independently challenge a package patch by testing the reported failure, its root cause, and likely regressions without editing the patch.
---

# Bug-fix verification

Run this review in the separate, ephemeral `adversarial-verifier` subagent
defined in `.claude/agents/adversarial-verifier.md`. Do not ask physical agents
A or B to interrupt their own assigned task to review the other's work.
The reviewer reads the original problem, reproduction, evidence card, and diff
and forms its own conclusion; do not prime it with the implementer's preferred
fix. It must not edit the patch, claim task ownership, or operate either VM.
The task owner remains responsible for live tests on their assigned VM and for
providing the reviewer with the resulting logs. If the evidence is insufficient
for an independent verdict, return `INCOMPLETE` and keep the task out of the
publish gate. The coordinator assigns and tracks work but does not substitute
for technical review.

Try to disprove the result:

1. Confirm the original scenario fails on the unmodified source/package.
2. Confirm the same scenario passes on the patched build.
3. Check a nearby input, lifecycle path, or alternate caller that could still
   trigger the root cause or expose a regression.
4. Check that the patch repairs the recorded invariant at the right layer and
   is no broader than needed.
5. Where applicable, inspect ownership and object lifetime, callbacks and
   cancellation, threading/reentrancy, error paths, and ABI/API/file-list
   effects.
6. Check the focused test, relevant existing tests, clean target-series build,
   and every compatibility/ABI/API/file-list claim made in the record.
7. Separate observed facts from inference and name anything not checked.

Return exactly one verdict:

```text
PASS
FAIL
INCOMPLETE
```

For `FAIL`, classify the problem using one or more of these fixed findings:

```text
FIX_INVALID
FIX_PARTIAL
TEST_INVALID
ROOT_CAUSE_UNPROVEN
PATCH_TOO_BROAD
```

For `PASS`, record `PATCH_CORRECT` as the review finding. The verdict controls
the state transition; the finding values explain why.

Include concise evidence for the verdict, a counterexample if found, and any
remaining unknowns. `PASS` means the stated reproduction and relevant checks
support the fix; it does not mean untested scenarios are safe. Only `PASS`
advances a behavior fix to `READY_TO_PUBLISH`.
