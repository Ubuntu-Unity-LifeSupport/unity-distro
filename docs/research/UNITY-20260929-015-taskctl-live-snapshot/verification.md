# UNITY-20260929-015 - independent verification

## Round 1 (2026-09-29, ephemeral Verifier subagent; commit ee6626a vs origin/main 8818028)

Verdict: **PASS** (PATCH_CORRECT). Review status: `INDEPENDENTLY_REPRODUCED`.

What the Verifier ran itself:

- **Before.** Given `main: unity-resolute-20260928-019 [snapshot]`,
  origin/main's name-only regex is false for `unity-resolute-20260927-021-r2`
  and true for the record's own name. This matches logs/01.
  - The new tests fail against origin/main's taskctl.py with 19
    AttributeErrors.
- **After.** `python3 -I live-dry-run.py` on the live aptly database, with
  read-only `snapshot search` only, returns CONFIRMED for the -021 record.
  - All 6 binaries match, arch `all` and `amd64`, the .ddeb included.
  - Exactly one source package matches, with the .dsc and the .tar.xz.
  - With one binary hash altered, the record is refused, and the refusal
    names that binary.
- **Tests.** The new module: 16 tests, OK, including the scratch aptly
  integration test. The full suite: 196 tests, OK, 1 skipped.
- **aptly query semantics**, probed read-only:
  - The plain `Architecture (amd64)` field does not match `all` packages;
    `$Architecture` does.
  - An unparseable query, `None` fields and `Architecture (source)` all give
    rc 1, which counts as missing.
  - `~` and `+` in versions parse fine.
  - `Version (=)` is dpkg-equal. That cannot cause a false accept, because
    acceptance needs exactly one line equal to the recorded sha256.
- **Fast path.** It compares exact `(name, kind)` tuples. A longer name that
  starts with the snapshot's name, or a `[local]` source with the same name,
  is not accepted.
- **Source rule.** It needs exactly one source key, then set equality of
  Checksums-Sha256 (.dsc included) against the source and source_file
  artifacts.
- **Condition (1).** It is enforced before the call: aptly_result and
  post_publish_check PASS, a matching gate, the build manifest, and the
  switch-time view of the record's snapshot.
- **Call site** in require_evidence: correct by reading.
- **Scope and import.** Only taskctl.py changed, plus tests and docs. The
  import is lazy, and the `sys.path` insert is explicit, so it also works
  under `-I`.

Counterexample: none found.

Remarks (non-blocking):

- The README said `$Architecture` for the binary query. It is now corrected
  to the plain field, which is what the code uses.
- The only "before" evidence from the new tests is AttributeErrors. The
  behavioural "before" is logs/01 plus the regex check above.
- Open question for C: the live snapshot may carry a newer version of the
  same package. This is not in the specification, so nothing refuses it.
- The check refuses safely in cases where it is stricter than it needs to
  be: several components, a binary query that matches more than once, a
  record without source_file.
- `publish show` and the searches are not atomic. Snapshots are immutable,
  so this is harmless.

Not checked:

- A real `publish show` run (forbidden) and its exact output format.
- `taskctl transition ... PUBLISHED` run end to end.
- A non-`.` prefix, or several components, on the live database.
