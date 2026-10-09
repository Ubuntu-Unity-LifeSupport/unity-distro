# Permission model 2026-10-09: phase registry

The permission-model change is run by the architecture session, outside the
coordinator's task board (May's decision of 2026-10-09). This file is its
ledger: one row per phase, with the branch, the commits, the tests, the
reviews, the result and the residual risks. Each phase is its own branch
from `main`, merged by the architecture session per ENGINEERING-PROCESS
section 10 after its tests and its independent review. May's eight
decisions are in `README.md`; the phase designs are in this directory.

| Phase | Scope | Branch | Design review | Verification | Merge | Result | Residual risks |
|---|---|---|---|---|---|---|---|
| P0 | Record of the review and May's decisions; section 9 names the effective settings file; this registry | `arch/permission-model-phase0` | fidelity check of the decision text (two rounds; 12 discrepancies fixed) | docs only; test suite run before merge | pending | pending | none |
| P1 | `command_guard.py` false-positive defects (UNITY-20260929-003 scope: RC1, RC1b, RC4, RC5; nothing else becomes allowed) | `arch/permission-model-phase1` | Design Challenger: round 1 REVISE, round 2 REVISE (always-on floor withdrawn), round 3 pending | Verifier after implementation; corpus replay (0 allow->deny); fresh-session checklist | - | not started (waits for APPROVE) | pre-existing floor gaps stay (private note) |
| P4 | Routine publication authority: `taskctl.py approve-publication`, approval record, publisher consumes it, PUBLISHED checks it; process text | `arch/permission-model-phase4` | Design Challenger: rounds 1-4 REVISE, round 5 APPROVE (2026-10-09) | Verifier after implementation; end-to-end harness; first routine publication after merge | - | in progress | the record is forgeable by the same OS user (accepted) |
| P3 | Claude Code permissions block (deny belt; ASK after measurement) | - | design drafted; measurement of ASK under `bypassPermissions` first | - | - | not started | ASK may be unavailable in the sessions' mode |
| P5 | Signer routine policy, publisher integration (UNITY-20260929-024), May's deployment steps | - | design drafted | - | - | not started; May's GO for the live steps | content-based policy; same-user forgery of builder-side records |
| P2 | Guard narrowing (rule A expansion trigger, interpreter strings) - after P5 | - | - | - | - | not started | - |
| P6 | Retire the live allowance; re-measure false positives - after P5 | - | - | - | - | not started | - |

Rules in force for every phase: no publication, live migration, key,
trust-policy or global-settings change is implied by the approval of the
architecture; the guard is not relaxed before P5 is verified; the exact
diff of any global-settings change is shown to May first; after a
protection change its effect is proven in new A, B and C sessions.
