# UNITY-20260927-045: scripts/build_sbuild.py - epochs, binaries from .changes, full log

Owner: agent B (builder; the board lists `target-desktop-2` because taskctl
takes no builder resource). Found in UNITY-20260927-021. Scope, fixed by the
coordinator: (1) Debian epochs when collecting artifacts, (2) binary
artifacts taken from this build's `.changes`, not by source-package name,
(3) the complete sbuild log in the manifest. Nothing else.

```yaml
task_id: UNITY-20260927-045
package: unity-distro scripts/build_sbuild.py (not a Debian package)
target_series: resolute
issue: local - build_sbuild.py cannot produce a manifest for packages with an
  epoch, silently drops binaries whose names do not contain the source name,
  and records only the dpkg-source lines of the build log
status: REPRODUCED
issue_search_result: NOT_FOUND  # project-local script (30499ff); no tracker
source_version: scripts/build_sbuild.py at 30499ff4232b9499fc6d5395bae114c674ade4fb
binary_version: n/a
source_commit: 30499ff4232b9499fc6d5395bae114c674ade4fb
observed: >
  (1) UNITY-20260927-021: sbuild "Status: successful" for
  calamares-settings-ubuntu 1:26.04.12+unity2, the script exits 2 "matching
  source and binary artifacts were not both found", no manifest.
  (2) by the same filter every binary whose file name does not contain the
  source name is skipped; see Reproduction.
  (3) the script's log of that build has 4 lines (the dpkg-source output, then
  the "$ sbuild" header), sbuild's own .build log of the same run 4377 lines.
expected: >
  (1) artifacts are found whatever the epoch; (2) the manifest lists exactly
  the files this build's .changes names, plus the source package; (3) the
  manifest's log is the whole sbuild output, header first.
reproduction: see Reproduction
root_cause: >
  build_sbuild.py:64-69 collects every *.deb/.dsc/.changes/.buildinfo/.udeb
  in the source's parent and the output dir and keeps a file only if
  `package in path.name and version in path.name`. `version` is
  dpkg-parsechangelog's Version, which carries the epoch ("1:26.04.12+unity2"),
  while Debian file names never do ("..._26.04.12+unity2_all.deb") - (1).
  Binary package names need not contain the source name
  (ubuntu-unity-meta -> ubuntu-unity-desktop, xorg-server -> xserver-xorg-core)
  - (2). `.ddeb` is not in the suffix set at all, so dbgsym packages never
  appear. (3) sbuild sets VERBOSE=0 when stdin/stdout is not a terminal
  (Sbuild/Conf.pm:1918-1921, sbuild 0.91.2ubuntu3); with VERBOSE=0 and a log
  file, the log stream goes only to the .build file (Sbuild/Build.pm
  3911-3930: `if ($nolog || $verbose) { print $saved_stdout $_ }`). The
  script redirects stdout to a file, so it gets only what runs before the
  log is set up (dpkg-source). The header is written through Python's
  buffered file object and reaches the file after the child's output.
root_cause_mechanism: >
  (1)/(2) name-substring filter with an epoch-bearing version and a source
  name; (3) non-tty stdout makes sbuild non-verbose, plus an unflushed header.
root_cause_evidence: docs/research/UNITY-20260927-045-build-sbuild/logs/
invariant: >
  The manifest names every artifact this sbuild run produced - the source
  package (.dsc) and every file in the run's .changes - with its hash, and
  its log is the complete output of that run in order.
existing_fix_result: NOT_FIXED  # origin/main still has 30499ff's version
candidate_approaches:
  - (1)+(2) read the run's .changes (Files / Checksums-Sha256) for the
    binaries and .buildinfo; locate .changes and .dsc by the version without
    epoch; keep the mtime guard
  - (1) only: strip the epoch in the substring filter - rejected: (2) stays
  - (3a) pass --verbose to sbuild so the stream is tee'd to stdout (sbuild
    keeps its own .build file too) and flush the header - chosen
  - (3b) --nolog (everything to stdout, no .build file) - rejected: drops
    sbuild's own log file, which people use today
  - (3c) copy the .build file into the output - rejected: finding it needs
    the same name guessing (epoch, arch, timestamped name) as the bug
chosen_approach: (1)+(2) via the .changes of this run; (3a)
why_chosen: >
  The .changes is dpkg's own list of what this build produced; it removes
  name guessing for binaries entirely. --verbose is sbuild's switch for
  exactly this.
alternatives_rejected:
  - see candidate_approaches
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # manifest schema keys unchanged; publish_aptly reads artifacts[].kind/package/version/architecture
design_challenger_required: false
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: >
  build_sbuild.py is the component that owns the build manifest; the
  defects are in its artifact selection and its log capture.
defensive_workaround_rejected: >
  Renaming or copying artifacts to match the filter, or post-editing
  manifests, would hide the selection bug instead of fixing it.
unknowns:
  - source-package component files (.tar.*, .orig.*, .debian.tar.*) are not
    listed in the manifest before or after; outside this task's scope
    (reported separately)
```

## Reproduction

`scripts/tests/test_build_sbuild.py` (stdlib `unittest`; run
`python3 -m unittest discover -s scripts/tests`) puts a stub `sbuild` on
`PATH` that behaves like sbuild 0.91 with stdout redirected to a file: it
prints only the dpkg-source line (the rest only with `--verbose`), writes the
full log to a `.build` file, and writes a `.dsc`, real `.deb`/`.ddeb` files
(`dpkg-deb --build`), a `.buildinfo` and a `.changes` naming them next to the
source tree.

Against the unmodified script (30499ff), `logs/01-tests-before-fix.txt`:

| test | before |
|---|---|
| `test_plain_version` (control) | pass |
| `test_epoch` (1) | FAIL: exit 2, "matching source and binary artifacts were not both found" |
| `test_binaries_not_named_after_source` (2) | FAIL: exit 2 |
| `test_partially_renamed_binaries_not_dropped` (2, xorg-server) | FAIL: exit 0 but `xserver-xorg-core` silently missing from the manifest |
| `test_unrelated_files_ignored` | FAIL: exit 2 (same cause as (2)) |
| `test_full_log` (3) | FAIL: log = dpkg-source line, then the header |

The case that matters most is the silent one: a manifest that looks
complete while a published binary is missing from it.

## Implementation

Plan, before the change (only `scripts/build_sbuild.py`, plus the tests):

1. After sbuild succeeds, find this run's `.changes` as
   `<source>_<version without epoch>_*.changes` in the source's parent or the
   output dir, newer than the build start; exactly one must exist.
2. Artifacts = the `.dsc` `<source>_<version without epoch>.dsc` (source)
   plus every file listed under `Checksums-Sha256:` of that `.changes`
   (binaries `.deb/.ddeb/.udeb` and `.buildinfo`), plus the `.changes`
   itself. Each listed file must exist and match the listed sha256; copy into
   the output dir as today. Binary metadata still from `dpkg-deb -f`.
3. sbuild command gets `--verbose`; the header line is flushed before the
   child starts. The manifest keeps its keys; `build_command` records
   `--verbose`.
4. Tests: the six in `scripts/tests/test_build_sbuild.py` pass; then real
   builds: calamares-settings-ubuntu (epoch), ubuntu-unity-meta (binary names
   differ), overlay-scrollbar (plain), each with a manifest compared against
   its `.changes`.

## Result

Change: commit `6596001` on `b/UNITY-20260927-045` (`scripts/build_sbuild.py`
+38/-13, new `scripts/tests/test_build_sbuild.py`).

**Tests** (`logs/02-tests-after-fix.txt`): 6 of 6 pass; before the fix 5 of 6
failed and the control passed (`logs/01-tests-before-fix.txt`).

**Real sbuild runs** (resolute chroot, `~/work/b/t045`, scripts at
`origin/main` = old and the branch = new; manifests and outputs in `real/`,
`check-manifest.py` compares a manifest with the `.changes` it names):

| source (case) | old script | new script |
|---|---|---|
| ubuntu-unity-meta 0.29+unity1 (binary `ubuntu-unity-desktop`) | exit 2, no manifest, log 4 lines | exit 0; `.dsc`, `.changes`, `.buildinfo`, `ubuntu-unity-desktop_…deb`; log 1831 lines; check PASS |
| calamares-settings-ubuntu 1:26.04.12+unity3 (epoch) | exit 2 (UNITY-20260927-021) | exit 0; 6 binaries incl. `-dbgsym.ddeb`; log 4463 lines; check PASS |
| unity-gtk4-menu 0.9 (control, plain) | exit 0, but the `-dbgsym.ddeb` of `.changes` missing, log 4 lines; check FAIL | exit 0; both binaries; log 3458 lines; check PASS |

An overlay-scrollbar run, meant as the plain control, failed in sbuild with
both scripts: its source format 1.0 packs the test repository's `.git` into
the diff (`real/run-osb-*.txt`). That is the test setup, not the script;
unity-gtk4-menu replaced it.

Behaviour change to note for the publisher: `.ddeb` (and `.udeb`) files of
the `.changes` are now `kind: binary`, so `publish_aptly.py` will expect the
dbgsym packages in the gated snapshot, as it expects every other binary of
the build.
