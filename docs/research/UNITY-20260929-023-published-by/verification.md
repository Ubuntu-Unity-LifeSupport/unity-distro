# UNITY-20260929-023 - independent verification

## Round 1 (e382ff1): FAIL, FIX_PARTIAL (INDEPENDENTLY_REPRODUCED)

A covered task reached PUBLISHED without its own Verifier PASS, on an unbound manifest; the evidence task_id was not checked. The path without published_by was unchanged. The record reading and the git checks had no bypass. Fixed in 25edb2d (README, "Verification round 1").

## Round 2 (25edb2d): PASS (INDEPENDENTLY_REPRODUCED)

- The round-1 counterexample is now refused.
- Each new check was exercised: task_id, verification FAIL, `..`, a symlinked directory, untracked, modified, a list field. A committed, unmodified manifest with PASS/REVIEWED is accepted.
- The path without published_by is identical to main in all 8 compared cases. `"published_by": null` is refused where main accepted it, which fails closed.
- 21 new tests and the full suite (253, 1 skipped) pass, and so does real-020.py.

Remarks, not blocking:

- The evidence's PASS/REVIEWED is taken as written, as in the existing DONE-from-REVIEW check.
- The manifest is bound by git history, not by a build tool.
- The git calls inherit the GIT_* environment.
