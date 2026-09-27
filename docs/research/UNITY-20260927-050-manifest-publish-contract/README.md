# UNITY-20260927-050: contract between build manifests and the aptly publisher

Owner: agent B (builder; the board lists `target-desktop-2`). Follows
UNITY-20260927-045. Scope from the coordinator: every artifact type that
`build_sbuild.py` now puts in a manifest (`.deb`, `.ddeb`, `.udeb`,
`.buildinfo`, `.dsc`, `.changes`; a binary whose version differs from the
source's, such as a binNMU or a `-dbgsym` with another version) either goes
into the snapshot and is checked by the publisher, or is excluded by an
explicit general rule written into the process. No exceptions for
particular tasks. Source component files in the manifest are UNITY-20260927-051,
not this task.

```yaml
task_id: UNITY-20260927-050
package: unity-distro scripts/publish_aptly.py (+ docs/ENGINEERING-PROCESS.md section 6)
target_series: resolute
issue: local - publish_aptly.py's snapshot expectations do not match what
  build_sbuild.py manifests contain since UNITY-20260927-045
status: REPRODUCED
issue_search_result: NOT_FOUND  # project-local scripts
source_version: scripts/publish_aptly.py at origin/main eb6553e (block from 30499ff)
binary_version: n/a
source_commit: eb6553e
observed: >
  logs/02-old-publisher.txt (the unmodified block, taken verbatim from
  origin/main, run on real .deb/.ddeb/.udeb fixtures): a binNMU binary and its
  dbgsym are rejected ("binary artifact version differs from candidate"); a
  .udeb is expected in the snapshot and accepted, although the publication
  has no debian-installer index (logs/01-aptly-behaviour.txt), so it would
  vanish from the published repository silently; a binary built from another
  source is accepted (only the manifest's own record is read, never the
  file); an artifact of an unknown kind is silently ignored, and so are
  .buildinfo/.changes, by omission rather than by rule.
expected: >
  Each artifact kind has one rule: in the snapshot and checked, or excluded
  by a written rule; nothing silently ignored.
reproduction: repro_old.py with scripts/tests/publish_fixtures.py
root_cause: >
  publish_aptly.py (origin/main) lines 228-243 predate 045: they build
  expected snapshot names from artifacts[].package/version/architecture of
  the manifest, force every binary's version to equal the source version,
  and fall through for any other kind.
root_cause_mechanism: >
  the check trusts the manifest record instead of the binary's control data,
  equates "binary version" with "source version" (dpkg records a differing
  source version as "Source: name (version)"), and has no rule for kinds
  other than source and binary.
root_cause_evidence: docs/research/UNITY-20260927-050-manifest-publish-contract/logs/02-old-publisher.txt
invariant: >
  A gated publication switches only to a snapshot that contains every binary
  and the source of this build, where "of this build" is established from the
  files themselves; every artifact kind in a manifest has an explicit rule.
existing_fix_result: NOT_FIXED
candidate_approaches:
  - publisher reads Package/Version/Architecture/Source/Package-Type from each
    binary file with dpkg-deb, requires them to match the manifest record,
    requires the binary's source (dpkg's Source rule) to be this source and
    version, expects <Package>_<Version>_<Architecture> in the snapshot;
    .udeb rejected; buildinfo/changes provenance-only; unknown kinds rejected
  - keep "binary version == source version" and exclude binNMUs - rejected: a
    binNMU or a dbgsym with its own version is a normal Debian case and the
    coordinator asked for no special exclusions
  - accept .udeb and add -with-udebs to the publication - rejected here:
    publication configuration is UNITY-20260927-047; until a debian-installer
    index exists, a udeb must fail loudly rather than disappear
chosen_approach: the first
why_chosen: >
  dpkg's own control data decides which source a binary belongs to; aptly
  names snapshot entries by exactly Package_Version_Architecture
  (logs/01-aptly-behaviour.txt: ddeb, udeb and a binNMU all appear so).
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # manifest schema unchanged; build_sbuild.py unchanged
design_challenger_required: false
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: >
  publish_aptly.py is the gate that decides what a snapshot must contain; the
  manifest producer (build_sbuild.py) already records every artifact.
defensive_workaround_rejected: >
  Filtering such artifacts out of manifests in build_sbuild.py would hide
  them from the gate instead of giving each a rule.
unknowns:
  - the publication has no source index (main/source absent): .dsc files are
    in snapshots but not published as Sources - publication configuration,
    UNITY-20260927-047
  - version_safety.py compares the apt candidate with the source version
    (candidate_binary_version == candidate_version); a binNMU apt candidate
    would fail there - UNITY-20260927-048
```

## Reproduction

`logs/01-aptly-behaviour.txt`: a scratch aptly 1.6.2 (own `rootDir`, not
`/srv/aptly`) given a `.dsc`, `.deb`, `.ddeb`, `.udeb` and a binNMU `.deb`:
all appear in `snapshot show -with-packages` as `name_version_arch`
(`demo-binnmu_1:1.0+b1_amd64`). The real `./resolute` publication has
`binary-amd64` only: `-dbgsym` packages are in its Packages index (7), there
is no `debian-installer` and no `source` index. (`aptly publish` itself is
blocked by the command guard, even for a scratch configuration; the udeb
index flag was only confirmed as present in the binary.)

`repro_old.py` runs the unmodified block (extracted from `origin/main` by its
first and last line) on `scripts/tests/publish_fixtures.py`:

| case | old publisher | contract |
|---|---|---|
| deb + ddeb, source version | entries | entries |
| binary named after the source, no Source field | entries | entries |
| binNMU binary + dbgsym (`Source: demo (1:1.0)`) | **rejected** | entries with `+b1` |
| udeb | **accepted** | rejected |
| binary from another source | **accepted** | rejected |
| binary version differs without a Source version | rejected (version) | rejected (source) |
| manifest record differs from the file | rejected (version) | rejected (mismatch) |
| unknown kind (`xz`) | **silently ignored** | rejected |

Order note: the implementation was first written while the task was still
in INVESTIGATING; it was set aside (`git checkout`), the evidence above was
recorded, and it was applied again only after IMPLEMENTING.

## Implementation

Plan:
1. `scripts/publish_aptly.py`: move the snapshot expectations into
   `snapshot_expectations()` with the rules above (and `control_fields()`,
   `binary_source()`); `main()` keeps the per-artifact hash check and calls it.
2. `docs/ENGINEERING-PROCESS.md` section 6: a short "Build manifest
   artifacts" rule list, the general rule the coordinator asked for.
3. Tests: `scripts/tests/test_publish_contract.py` runs the same fixtures
   through `snapshot_expectations()`; all eight cases must give the contract's
   result (the old block fails six, `logs/02-old-publisher.txt`).

## Result

- `scripts/publish_aptly.py`: `snapshot_expectations()`, `control_fields()`,
  `binary_source()`, `PROVENANCE_ONLY_KINDS`; `main()` keeps the hash check
  per artifact and calls `snapshot_expectations()` (+66/-10).
- `docs/ENGINEERING-PROCESS.md` section 6: "Build manifest artifacts", the
  rule per kind.
- `scripts/tests/test_publish_contract.py` with
  `scripts/tests/publish_fixtures.py`: all eight contract cases and the dpkg
  Source rule pass; the 045 tests still pass (`logs/03-tests-after.txt`,
  8 of 8). The old block gets six of the eight cases wrong
  (`logs/02-old-publisher.txt`).
- Integration on real manifests from UNITY-20260927-045
  (`logs/04-integration-real-manifests.txt`, `integration.py`): the files of
  calamares-settings-ubuntu 1:26.04.12+unity3 (epoch, a `-dbgsym.ddeb`),
  ubuntu-unity-meta 0.29+unity1 (binary `ubuntu-unity-desktop`) and
  unity-gtk4-menu 0.9 put into a scratch aptly 1.6.2 and snapshotted: every
  entry `snapshot_expectations()` requires is present, matched with the
  publisher's own pattern.

Not measured: a real `publish_aptly.py` run end to end (needs 046-048) and
`aptly publish` itself (blocked by the command guard).
