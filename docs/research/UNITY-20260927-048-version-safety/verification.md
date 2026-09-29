# UNITY-20260927-048 independent verification

Two rounds by ephemeral `adversarial-verifier` subagents (read-only; no VM,
no edits, no `aptly publish`).

## Round 1 (f415a56): FAIL, FIX_PARTIAL - INDEPENDENTLY_REPRODUCED

Reproduced the old circularity with origin/main (honest record UNSAFE,
typed candidate SAFE) and ran the new flow against the real archive and
scratch snapshots: calamares with `Architecture: all` SAFE; a snapshot older
than the archive UNSAFE; a binary of another source name picked from the
archive UNSAFE; a version missing its epoch REPLACES_SECURITY_UPDATE; a binNMU
SAFE; a forged gate-time view passes the gate but not the switch, whose
re-measurement is unconditional. Findings: taskctl still required the removed
`fresh_apt_policy` (a publication could never reach PUBLISHED); `docs/apt`
inputs were not tied to the repository; minor, the model Release identity
was fixed. Fixed in 3adbbd0 (README, "First verification: FAIL, and the
fixes").

## Round 2 (3adbbd0): PASS (PATCH_CORRECT) - REVIEWED

Ran the 30 script tests (none skipped, aptly integration included); checked
the publisher's `docs/apt` tracked-clean requirement on a scratch clone
(clean: accepted; modified tracked preference, untracked preference, staged
but uncommitted sources: refused); grepped scripts/, docs/, .claude/ and
~/coordinator for consumers of removed fields (none live); confirmed the
default model identity equals the live Release (`. resolute`) and what the
publisher passes for prefix `.`.

Non-blocking notes and what was done:
1. The section 6 example used another prefix while the gate-time `--release`
   default is `. resolute` - the example now passes `--release` for the
   gate's prefix and distribution, and the text says the publisher refuses a
   different model identity (fails closed either way).
2. `logs/05-tests-after.txt` was stale (26) - refreshed: 30 of 30.
3. A subdirectory in `docs/apt/preferences.d` would block publishing - fails
   closed; left as is.

Remaining unknowns: no end-to-end `publish_aptly.main()` or taskctl
PUBLISHED transition against a real record (needs 046/047); a non-`.` prefix
was not measured (none exists).
