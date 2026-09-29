# UNITY-20260927-051: source package files in the build manifest

Owner: agent B (builder; the board lists `target-desktop-2`). Scope from the
coordinator: the source package's component files (`.orig.tar.*`,
`.debian.tar.*`, native `.tar.*`, `.diff.gz`) must be in the build manifest
with the sha256 from this build's `.dsc`/`.changes`, and
`publish_aptly.snapshot_expectations()` needs an explicit rule for them in the
spirit of UNITY-20260927-050 - checked in the snapshot or provenance only,
justified by how aptly stores sources. A source-full `.changes` must no longer
be refused as an unknown kind (gap 4 of 050). Nothing else; 046/047 and the
live `/srv/aptly` are not touched.

```yaml
task_id: UNITY-20260927-051
package: unity-distro scripts/build_sbuild.py, scripts/publish_aptly.py
target_series: resolute
issue: local - provenance gap: source component files are not in manifests
status: REPRODUCED
issue_search_result: NOT_FOUND  # project-local scripts
source_version: origin/main 62b49c5
binary_version: n/a
source_commit: 62b49c5
observed: >
  logs/01-reproduction.txt: the calamares-settings-ubuntu 1:26.04.12+unity3
  manifest lists the .dsc but not the 11.8 MB .tar.xz the .dsc names; the
  file is not even copied to the output dir. A source-full .changes (sbuild
  configured to include the source) would list the .tar.* too; build_sbuild.py
  would record it as kind "xz" and publish_aptly.py rejects that kind
  (050, gap 4).
expected: >
  Every file the .dsc names is in the manifest with the .dsc's sha256, copied
  next to the manifest; the publisher checks that the snapshot's source
  package consists of exactly these files with these hashes.
reproduction: logs/01-reproduction.txt; tests in scripts/tests
root_cause: >
  build_sbuild.py (since 045) takes the .dsc plus the files of the .changes;
  a binary-only .changes (sbuild's default) names no source files, and
  nothing reads the .dsc's own file list. Kinds are derived from the suffix,
  so a source file in a source-full .changes becomes an unknown kind.
root_cause_mechanism: >
  the component list lives only in the .dsc (Checksums-Sha256), which the
  script never parses.
root_cause_evidence: docs/research/UNITY-20260927-051-source-files/logs/01-reproduction.txt
invariant: >
  A manifest names every file of the source package it built, with the hash
  the .dsc records, and a gated publication switches only to a snapshot whose
  source package is exactly those files.
existing_fix_result: NOT_FIXED
candidate_approaches:
  - build_sbuild.py parses the .dsc's Checksums-Sha256, finds each file next
    to the .dsc, checks its sha256, copies it and records it as kind
    "source_file"; a .changes entry that is the .dsc or one of its files is
    not recorded twice. publish_aptly.snapshot_expectations() accepts
    "source_file" only as part of the .dsc's list (the set must match the
    .dsc exactly); before the switch the publisher reads the snapshot's source
    package with `aptly snapshot search -format '{{index . "Checksums-Sha256"}}'
    <snapshot> 'Name (<src>), $Architecture (source), Version (= <ver>)'` and
    requires exactly the manifest's .dsc and source files with the same sha256
    (checked in the snapshot)
  - provenance only (hash in the manifest, not compared with the snapshot) -
    rejected: aptly keeps a source package as one record with all its files
    and their Checksums-Sha256 (logs/01), and a snapshot can hold a different
    source under the same name and version (a rebuilt or regenerated source,
    as happened with unity-lens-files +unity1); the name_version_source entry
    050 checks cannot tell them apart, the file hashes can
chosen_approach: the first
why_chosen: >
  aptly exposes exactly the per-file sha256 of the source package inside the
  named snapshot (read-only), so the check costs one query and closes the
  "same name and version, other content" case.
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # new manifest kind "source_file"; manifest keys otherwise unchanged
design_challenger_required: false
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: >
  build_sbuild.py owns the manifest's artifact list; publish_aptly.py owns what
  the snapshot must contain - the same split as in 045/050.
defensive_workaround_rejected: >
  Dropping unknown suffixes from source-full .changes would silence gap 4
  instead of giving source files a rule.
unknowns:
  - the live publication has no Sources index (050, 047): source packages are
    in snapshots, not published as Sources
  - source files are now copied into build output dirs under docs/research;
    they are large and must not be committed - .gitignore gets patterns for
    them next to the existing *.deb rules
```

## Reproduction

`logs/01-reproduction.txt`: the 045 manifest of calamares-settings-ubuntu
1:26.04.12+unity3 has no `.tar.xz`, although its `.dsc` names one
(`43ac3997…`, 11799976 bytes); a scratch aptly holding that source shows one
`calamares-settings-ubuntu_1:26.04.12+unity3_source` entry whose
`Checksums-Sha256` lists the `.dsc` and the `.tar.xz`.

Tests against the unmodified script (`logs/02-tests-before-fix.txt`):
`test_source_files_recorded` fails for all three layouts (native `.tar.xz`;
3.0 quilt `.orig.tar.gz` + `.debian.tar.xz`; 1.0 `.orig.tar.gz` + `.diff.gz`):
no `source_file` artifacts at all; `test_source_full_changes` fails: the
`.dsc` is recorded twice and the source files get suffix kinds. The other
tests pass.

## Implementation

1. `scripts/build_sbuild.py`: parse the `.dsc`'s `Checksums-Sha256`; each file
   must exist next to the `.dsc` and match; record it as `source_file` (with
   package and version) and copy it; entries of the `.changes` that are the
   `.dsc` or one of its files are not recorded again.
2. `scripts/publish_aptly.py`: `snapshot_expectations()` accepts
   `source_file` only as exactly the `.dsc`'s list (read from the manifest's
   copy of the `.dsc`); before the switch, `source_package_matches()` compares
   the snapshot's source package (`aptly snapshot search -format '{{index .
   "Checksums-Sha256"}}'`) with the manifest's `.dsc` and source files.
3. `docs/ENGINEERING-PROCESS.md` section 6 rule list; `.gitignore` patterns
   for source files in build output dirs.
4. Tests: the two above pass; publisher tests for the `.dsc`-list rule and the
   snapshot comparison; a scratch aptly run with a real source package.

## Result

- `scripts/build_sbuild.py` (+29/-12): the `.dsc`'s `Checksums-Sha256` files
  are checked, copied and recorded as `source_file`; a source-full
  `.changes` no longer duplicates the `.dsc` or yields unknown kinds.
- `scripts/publish_aptly.py`: `source_file` must be exactly the `.dsc`'s list
  (`snapshot_expectations()`); before the switch the snapshot's source package
  is read with `aptly snapshot search -format '{{index . "Checksums-Sha256"}}'
  <snapshot> 'Name (<src>), $Architecture (source), Version (= <ver>)'` and
  `source_package_matches()` requires exactly the manifest's `.dsc` and source
  files with their sha256.
- `docs/ENGINEERING-PROCESS.md` section 6: the `source_file` rule;
  `.gitignore`: source tarballs and `.diff.gz` in build output dirs.
- Tests: 35 of 35 (`logs/04-tests-after.txt`), new: the three source
  layouts and a source-full `.changes` (`test_build_sbuild.py`), the
  `.dsc`-list rule, the snapshot comparison and the parsing of aptly's
  output (`test_publish_contract.py`).
- Real (`logs/03-integration.txt`, `integration.py`): a `build_sbuild.py`
  build of unity-gtk4-menu 0.9 records `unity-gtk4-menu_0.9.tar.xz` as
  `source_file`; in a scratch aptly (A) its own source gives MATCH, (B) a
  source regenerated from the same tree with README.md changed - same name
  and version - is refused (both `.dsc` and `.tar.xz` hashes differ). A first
  B run changed `.gitignore`, which dpkg-source leaves out of a native
  source, so the tarball was identical and MATCH was correct; the harness was
  fixed to change a file the source contains.

Not measured: 3.0 (quilt) and 1.0 layouts in a real build (fixtures only);
an end-to-end `publish_aptly.py` run (046/047).

## Verification

**PASS**, **INDEPENDENTLY_REPRODUCED** at script level (`verification.md`).
Manifests made before this change carry no `source_file` entries and are now
refused by the publisher (fail closed): builds for pending gates must be
repeated with this `build_sbuild.py`.
