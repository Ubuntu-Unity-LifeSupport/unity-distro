# UNITY-20260929-015 - taskctl PUBLISHED after a later publication

Kind: `tool` (`scripts/taskctl.py`). Owner: B.

## Reproduction

This task blocks UNITY-20260927-021 from reaching PUBLISHED. The real refusal
is in logs/01:

- `taskctl.py transition UNITY-20260927-021 PUBLISHED` fails with
  `live aptly publish show does not confirm the recorded snapshot`.
- The publish record names `unity-resolute-20260927-021-r2`, with
  post-publication checks PASS.
- UNITY-20260928-019 later switched `./resolute` to
  `unity-resolute-20260928-019`.
- That snapshot still carries every -021 artifact with the same version and
  sha256; `snapshot diff` shows only 11 lightdm additions.

The same refusal will hit any package whose target verification finishes
after the next switch. With several agents publishing, that is the normal
case.

## Existing fix

`NOT_FIXED`:

- `origin/main` 8818028 has the name-only check that 30499ff introduced.
- No remote branch changes `scripts/taskctl.py` against `main`.
- No task on the board covers it. The only near one is UNITY-20260929-009,
  about ENGINEERING-PROCESS section 6 wording.

## Root cause

`require_evidence(..., "PUBLISHED")` treats "the record's snapshot is live
now" as proof that the task's publication is live. The first proof is
sufficient but not necessary. A later publication replaces the name, yet the
live snapshot can still hold every artifact.

Mechanism: the only check is
`re.search(rf"...{record['snapshot']}\s+\[snapshot\]", publish show)`.

## Invariant

PUBLISHED means that what the record says was published is live now, the
same bytes. It does not mean that the live snapshot has a particular name.

## Chosen approach

Keep the name check as the fast path. When it fails, taskctl confirms the
record by content, and only through read-only aptly commands.

The content path accepts only if all of these hold:

1. The record passes every existing PUBLISHED check. That includes
   `aptly_result` PASS and `post_publish_check` PASS, which the publisher
   writes only after `publish show` named the gated snapshot at switch time.
   So the record's snapshot was live when it was published.
2. `publish show` names exactly one live snapshot for the distribution and
   prefix.
3. That snapshot contains every artifact of the record:
   - For each `binary` artifact (.deb/.ddeb): `snapshot search -format
     '{{index . "SHA256"}}' <live> 'Name (<package>), Version (= <version>),
     Architecture (<architecture>)'` returns exactly one line, and that line
     is the artifact's sha256. This is the plain field, per Design Challenger
     finding 3; `$Architecture (amd64)` would also match `all`.
   - For `source` and `source_file` artifacts: the live snapshot's source
     package `Name (<package>), $Architecture (source), Version (= <version>)`
     has exactly the .dsc and source files with those sha256.
     `publish_aptly.dsc_checksums` and `source_package_matches` are reused, so
     the source rule is the publisher's own switch-time rule.
   - `buildinfo`/`changes` are provenance only; aptly does not store them.
     This matches `publish_aptly.PROVENANCE_ONLY_KINDS`.
   - Any other kind is refused.

Everything else is refused, and the refusal names the missing artifact or
the one with a different hash. `publish` in any other form is never run.

## Correct layer

The PUBLISHED gate in `taskctl.py` makes this decision. Reading a snapshot's
source files uses the publisher's helpers, so the source comparison is not
duplicated.

- Not in `publish_aptly.py`: publishing is finished by the time this check
  runs, and the publisher must not rewrite records afterwards.
- Not by editing the evidence `snapshot` field: the record must stay true.

## Rejected

- **Accept any live snapshot that `snapshot diff` shows as a superset.**
  Diff reads package keys, not file hashes. It also needs the record's
  snapshot to still exist, and it would accept a rebuilt same-version
  artifact.
- **Check by package name and version only**, as the publisher does for
  binaries at switch time. Here we want bytes: a same-version rebuild with
  different content must be refused.
- **Record a "superseded by" field by hand.** That is a human claim, which
  taskctl cannot check.

## Design Challenger (2026-09-29, independent subagent, short review)

Verdict: **APPROVE**, with non-blocking findings. They are taken into the
design as follows:

1. Taken. The content path refuses a record that does not have exactly one
   `source`, at least one `binary`, and `source_file` entries. It does not
   rely on the publisher having checked this at switch time.
2. Taken. The source query must match exactly one source package
   (`-format '{{.Key}}'`, one line) before its Checksums-Sha256 is compared.
3. Taken. Binaries are queried with the plain field `Architecture (<arch>)`,
   because `$Architecture (amd64)` also matches `all`.
4. Taken. `publish show` must list exactly one source line, and it must be
   `[snapshot]`. Several components, or a `[local]` source, are refused.
   There is a test for the two-component case.
5. No change needed. `post_publish_check` PASS on the write-once record is
   the same trust the fast path already relies on. The record's snapshot
   does not have to exist any more.
6. Not implemented. The finding: the live snapshot may also carry a newer
   version of the same package. The coordinator's specification does not
   include this condition, so it is left to C as an open question.
7. Confirmed by logs/01: epochs, `+` and .ddeb work, and queries are passed
   as argv.
8. Taken. Only `dsc_checksums` and `source_package_matches` are imported from
   `publish_aptly`. taskctl keeps its own aptly runner, which is the one
   the tests replace.
9. Taken. Tests for 1, 2 and 4 are added, and the test file is written with
   the Write tool.

## Tests

`scripts/tests/test_taskctl_live_snapshot.py`:

- **Unit tests** with a fake aptly runner:
  - live name equal to the record's (fast path);
  - a later superset snapshot is accepted;
  - refusals: a binary missing, a binary with a different sha256, a binary
    only at another version, a source file with a different hash, a source
    package missing, two live snapshots, `publish show` failing, an
    unsupported artifact kind.
- **Integration test** against a scratch aptly root (skipped without aptly):
  - two real snapshots: the record's, and a later one with one more package;
  - a third snapshot where the binary was replaced by a same-version rebuild
    with other bytes;
  - `publish show` is the only faked answer.
- The old code fails the "later superset accepted" test. That is the
  regression test.

## Validation (2026-09-29)

- logs/02: all 16 new tests pass, including the real-aptly integration
  test (a superset snapshot is accepted; a same-version rebuild and a removed
  binary are refused). The full suite passes: 196 tests, OK, 1 skipped (an
  existing skip).
  - Run against `origin/main`'s taskctl.py, the new tests error with 19
    AttributeErrors, because there is no content check there.
  - The behavioural "before" is the real refusal in logs/01.
- logs/03 (`live-dry-run.py`) uses the real UNITY-20260927-021 publish record
  and the real live aptly database. Only read-only `snapshot search` runs.
  `publish show` is answered from UNITY-20260928-019's write-once record
  (`unity-resolute-20260928-019`) instead of being run.
  - Result: CONFIRMED. All 6 binaries (`Architecture (all)` and `(amd64)`,
    .ddeb included) match, and exactly one source package carries exactly
    the recorded .dsc/.tar.xz sha256.
  - The same record with one binary hash altered is refused, and the refusal
    names that binary.
- Not covered by a test: the call site in `require_evidence` (three lines)
  is not driven end to end. The PUBLISHED path needs a full gate, build
  manifest and publish record fixture set. Its logic lives in
  `confirm_live_publication`, which the tests do drive.

## Newer version in the live snapshot (decided)

Design Challenger finding 6: the live snapshot may carry every artifact of
the record and also a newer version of the same package. The bytes are
live, but apt installs the newer one.

**Deliberate decision (C, 2026-09-29): not a refusal.** PUBLISHED means
"these bytes were published and are still in the live publication". It does
not mean "apt will choose them". Which version apt selects is for the later
task that published the newer version to check. Also recorded in
`docs/DECISIONS.md`.
