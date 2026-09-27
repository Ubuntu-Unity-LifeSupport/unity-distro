# UNITY-20260927-056 independent verification

Ephemeral `adversarial-verifier` subagent (read-only; no VM, no edits, no
`aptly publish`), 2026-09-27, branch `b/UNITY-20260927-056` at `61ca534`;
origin/main (e9f3dfc) and HEAD extracted with `git archive` into its scratch
dir.

- verification_result: **PASS** (finding: PATCH_CORRECT)
- review_status: **INDEPENDENTLY_REPRODUCED**

| run | origin/main | HEAD |
|---|---|---|
| original test, TMPDIR with `_`, 10 runs | 0 pass (`[] != ['<model>_Release']`) | 10 pass |
| original test, TMPDIR with `~ = @ +`, 10 runs | 0 pass | 10 pass |
| original test, plain TMPDIR, 10 runs | 8 pass | 10 pass |
| original test, default TMPDIR, 240 runs (old) | 37 fail (15%; expected 0.197, compatible) | - |
| new regression test | both subtests fail | pass |
| full suite (36 tests): 30 default, 10 with `_`, 5 with `~=@+` | - | all pass |

A probe with two full views on fixtures (one under a `_` TMPDIR): no nonce or
Description in the view JSON, model entry keys unchanged, `compare_views()`
clean, policy and verdict unchanged.

Checked: the real resolute Release itself carries `Description: Ubuntu
Resolute 26.04` (the owner's prompt assumed archives have none); harmless -
only this run's exact 128-bit nonce matches, and Description is dropped from
every entry. apt pins on o/l/a/n/c/v/b, never Description; `list_sha256`
comes from the snapshot list; `compare_views()` skips model entries;
version_safety.py and taskctl.py do not read `releases`. The changed test
assertion is not masking: the positive `== ["<model>_Release"]` is strict and
the `_model_` check catches an unmarked model Release. No remaining
nondeterminism found (fixture Dates equal, sorted globs, no network in tests).
Scope: `scripts/apt_view.py` and the test file only.

Remaining unknowns: TMPDIR with spaces or `%` not tried (would concern the
existing sources/apt.conf quoting, not this fix); the real-archive run is the
owner's `logs/06`.
