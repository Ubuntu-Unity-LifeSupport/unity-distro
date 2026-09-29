# UNITY-20260927-051 independent verification

Ephemeral `adversarial-verifier` subagent (read-only; no VM, no edits, no
`aptly publish`), 2026-09-27, branch `b/UNITY-20260927-051` at `860df32`.

- verification_result: **PASS** (finding: PATCH_CORRECT)
- review_status: **INDEPENDENTLY_REPRODUCED** at script level (stub sbuild as
  in the tests, scratch aptly); no real sbuild run; the real t051 build output
  was checked.

What it ran: the tests (35/35); the same tests with `build_sbuild.py` and
`publish_aptly.py` from origin/main (8 failures, 2 errors, all in the new
tests; the 045/048/050 tests pass on both); dpkg-source fixtures - 3.0 (quilt)
with `.orig.tar.gz`, `.orig.tar.gz.asc`, `.orig-comp.tar.gz`,
`.debian.tar.xz`, and native 1.0 `.tar.gz`, each also PGP-armored, CRLF and
with a multi-line field after Checksums-Sha256 - parsed correctly; scratch
aptly 1.6.2: the source query works with an epoch, its output (leading
spaces, empty trailing line) is parsed; a source with the same name and
version but another `.debian.tar.xz` is refused; one snapshot could not be
made to hold two source records with the same name and version (`repo add`
refuses the second; `snapshot merge -no-remove` and `snapshot pull
-no-remove -all-matches` keep one); `snapshot_expectations()` on the real t051
manifest records the `.tar.xz` and passes; `.gitignore` ignores `.orig.tar.gz`,
`.orig.tar.gz.asc`, `.orig-comp.tar.xz`, `.debian.tar.xz`, `.diff.gz` and not
`.dsc`, manifests or logs.

Code review: in a source-full `.changes` a source file whose hash differs from
the `.dsc`'s fails a check against the file on disk and the build exits 2;
the snapshot source check runs after the artifact hash loop and before the
switch-time apt view and the switch, with no early exit, and fails closed on
an aptly error or empty result. Scope: the three items, the process text and
`.gitignore`.

Minor, left as is: the `source_file` comment in `publish_aptly.py` sits after
the "anything else" line (cosmetic); `test_dsc_list_rule` uses short hashes
(real formats are covered by `integration.py` and the verifier's fixtures).

Remaining unknowns: manifests made before 051 have no `source_file` entries,
so the publisher refuses them (fails closed; pending gates rebuild); no real
sbuild of 3.0 (quilt) or 1.0 sources; no end-to-end `publish_aptly.py` run;
the aptly query with package names containing `+` was not tried (a failing
query refuses the switch); if some untested aptly path ever put two source
records with the same name and version into one snapshot, their outputs
would merge and the last hash per file name would win.
