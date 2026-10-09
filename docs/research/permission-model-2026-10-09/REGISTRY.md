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
| P0 | Record of the review and May's decisions; section 9 names the effective settings file; this registry | `arch/permission-model-phase0` | fidelity check of the decision text (two rounds; 12 discrepancies fixed; final check clean) | docs only; 417 tests OK on the branch and on the merge | `main` 7f060ea (2026-10-09 10:14Z), DECISIONS 75a3eb1 | done | none |
| P1 | `command_guard.py` false-positive defects (UNITY-20260929-003 scope: RC1, RC1b, RC4, RC5; nothing else becomes allowed) | `arch/permission-model-phase1` | Design Challenger: rounds 1-7 REVISE (each with a verified remedy), round 8 APPROVE (2026-10-09) | implementation agrees with the approved simulation on 229 probes; 16/16 corpus records; 0 changes on 195 test commands; transcript replay 11216 commands, 0 allow->deny, 257 deny->allow all RC1/RC1b; Verifier PASS, INDEPENDENTLY_REPRODUCED (own replay 11233 commands, sandboxed execution of every allowed adversarial form); live hook checked in the architecture session after the merge (apostrophe heredoc allowed; pgrep -f, rm -rf with an unguarded variable, git add -A denied; --check OK) | `main` 7ac636c (2026-10-09 12:08Z); 472 tests OK on the merge | done | pre-existing floor gaps stay (private note, incl. a quoted-separator form for a separate tightening decision) |
| P4 | Routine publication authority: `taskctl.py approve-publication`, approval record, publisher consumes it, PUBLISHED checks it; process text | `arch/permission-model-phase4` | Design Challenger: rounds 1-4 REVISE, round 5 APPROVE (2026-10-09) | 37 new tests (`test_approval_record.py`, `test_publish_authority.py`) through the real scripts in `publish_harness.py`; full suite; Verifier round (see `phase4-publication-authority.md`); the first routine publication after the merge is C's and the owner's ordinary publication under decision 2, not part of this approval | `main` 258dc46 (2026-10-09 10:53Z); cut-over 2026-10-09T10:49:00Z; 468 tests OK on the merge | done | the record is forgeable by the same OS user (accepted); the validity window is checked before the switch only |
| P3 | Claude Code permissions block (deny belt, ASK for trusted files and external writes, one guard rule for shell writes into trusted files) | `arch/permission-model-phase3` | measured 2026-10-09: ask rules and hook ask decisions are honoured under `bypassPermissions` (three throwaway sessions, live settings untouched); Design Challenger round 1 pending | - | - | in progress; `--apply` only after May sees the diff and confirms | the prompt reaches whoever is at the desktop app |
| P5 | Signer routine policy, publisher integration (UNITY-20260929-024), May's deployment steps | - | design drafted | - | - | not started; May's GO for the live steps | content-based policy; same-user forgery of builder-side records |
| P2 | Guard narrowing (rule A expansion trigger, interpreter strings) - after P5 | - | - | - | - | not started | - |
| P6 | Retire the live allowance; re-measure false positives - after P5 | - | - | - | - | not started | - |

Rules in force for every phase: no publication, live migration, key,
trust-policy or global-settings change is implied by the approval of the
architecture; the guard is not relaxed before P5 is verified; the exact
diff of any global-settings change is shown to May first and needs his separate confirmation; after a
protection change its effect is proven in new A, B and C sessions.
