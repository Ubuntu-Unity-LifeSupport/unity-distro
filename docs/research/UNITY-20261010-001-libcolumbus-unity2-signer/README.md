# libcolumbus +unity2: UNITY-20261010-001, a no-change rebuild for the archive signer

Owner: agent B (target2). One revision, `1.1.0+15.10.20150806-0ubuntu39+unity2`, on the published +unity1
(`3da4d89`, UNITY-20261008-013).

```yaml
task: UNITY-20261010-001
package: libcolumbus
target_series: resolute
source_version: 1.1.0+15.10.20150806-0ubuntu39+unity1 (published 2026-10-09)
candidate_version: 1.1.0+15.10.20150806-0ubuntu39+unity2
change: debian/changelog only
purpose: the first routine publication through the aptly-signer (permission model phase 5): an upgrade of a
  source package already in the live publication, which the signer's routine policy should sign without May
```

## Why there is no defect here

There is no bug to reproduce and no code to change. C asked for a no-change rebuild so that a real
publication goes through the signer's routine policy. That policy signs, without May, an upgrade of one
already-known source package that has at most 40 binary records, unchanged maintainer scripts and stays
within the rate limits (ENGINEERING-PROCESS section 6).

The defect fields of the task evidence are filled accordingly:

- **Reproduction:** the rebuild itself. Reproducible means the build passes again in a clean resolute
  chroot.
- **Root cause:** none. The task exists for an operational reason, the P5 auto-sign check.
- **Existing fix and issue search:** not applicable, because there is no defect.
- **No Design Challenger:** nothing is designed.

## The change

libcolumbus `b/UNITY-20261010-001` (`63c6950`, on `3da4d89`) adds one changelog entry:

```text
libcolumbus (1.1.0+15.10.20150806-0ubuntu39+unity2) resolute; urgency=medium

  * No-change rebuild to exercise the archive signer's routine policy.

 -- NeiroNext <mihail.rozshko@gmail.com>  Sat, 10 Oct 2026 16:56:57 +0000
```

`git diff --stat 3da4d89 63c6950`: `debian/changelog | 6 ++++++`. No other file changed.

## Build (2026-10-10)

`scripts/build_sbuild.py --task-id UNITY-20261010-001 --source-repo packages/libcolumbus`, chroot
`resolute-amd64-20261008T083223Z` (2 days old, within the 7-day rule; the chroot of the +unity1 build).
Manifest `build/UNITY-20261010-001-libcolumbus-build-manifest.json`: PASS, source commit `63c6950`. 18 of 18
tests pass. Artifacts: the source, 4 `.deb` (libcolumbus1v5, libcolumbus1-common, libcolumbus1-dev,
python3-columbus) and 2 `.ddeb`.

## The binaries against the published +unity1 (logs/02, logs/03)

`payload.sh` compares the published +unity1 pool files with this build, package by package:

- **File lists:** identical for all 4 `.deb`.
- **Control fields:** identical apart from the version.
- **Control members:** the same set (`md5sums`, `shlibs`, `symbols`, `triggers`).
- **`libcolumbus.so.1`:** 196 exported symbols, DT_NEEDED and SONAME all identical.
- **`md5sums`:** they differ, because the compiled files and `changelog.Debian.gz` differ.

`elfcmp.sh` shows why the compiled files differ (logs/03). It reads every section's bytes by file offset and
size, so non-allocated sections are compared too. In `libcolumbus.so.1.1.0` and in the Python module, 27 of 30
ELF sections are byte-identical (the null section not counted). The other three are:

- `.note.package`, which carries the package metadata JSON with the version
  (`...ubuntu39+unity1` → `...ubuntu39+unity2`);
- `.note.gnu.build-id`, which is derived from the file contents and so changes with the note;
- `.gnu_debuglink`, which names the debug file by its build-id.

The machine code and data (`.text`, `.rodata`, `.data`, the dynamic symbol and version tables) are unchanged.

`elfcmp.sh` compares sections only. It does not cover the ELF header, the program headers, the section header
table or the padding between sections. The Verifier's `zerocmp.py` closes that gap (logs/05): with the three
sections zeroed, both stripped files are byte-identical as whole files. That covers the ELF header, the
program headers, the section header table and the 5905 (3588) bytes outside sections.

The `.ddeb` debug files differ by more than their build-id names. Everything that differs comes from the
version:

- `.debug_line_str` carries the `/usr/src/libcolumbus-<version>/` paths;
- `.symtab` and `.strtab` carry LTO private-symbol hash suffixes, which are derived from the version;
- so the compressed debug sections have other bytes, and python3-columbus-dbgsym is 8 bytes shorter.

The Verifier normalised the version and the string offsets and found identical DWARF info, decoded line tables
and symbol lists. The difference is debug-only: the runtime files are identical apart from the three notes.

`payload.sh` compares file lists by permissions and name only. The Verifier also compared size, owner and link
target: only the sizes of the `changelog.Debian.gz` files differ, and each new changelog is the old one plus
the new entry.

## Target check (target2, 2026-10-10, logs/04)

- **Setup:**
  - target2 was found running, booted at 15:17Z with a GUI session, and clean inside. It was powered off,
    restored to Clean-2 and confirmed from inside: no `~/.dirty`, no work directories, only `ubuntu.sources`,
    libcolumbus `0ubuntu39`.
  - The live archive was added the usual way. `apt full-upgrade` installed the published stack, libcolumbus
    +unity1 included, and left nothing to upgrade.
  - The installed libcolumbus binaries, libcolumbus1v5 and libcolumbus1-common, were then upgraded to +unity2
    from a file repository of this build. Their sha256 equal the build's; `dpkg -V` is clean.
  - The file repository's index was made on the builder, because apt-utils is not installed on target2. The
    first try on the guest left an empty index, and the install refused it.
- **The session:** a cold cycle, then the auto-login session.
- **Mappings:** hud-service and the applications scope (`unity-scope-loader`) map the installed
  `libcolumbus.so.1.1.0` (the same inode), with no deleted library mappings.
- **HUD:** a query gives results, and its Matcher is built and freed (0 → 3 → 0). `leak.sh`: 0 deleted
  temporary files at every step (10 queries, 10 Mines starts, 10 Writer starts, 10 queries in Writer, 60 s
  idle).
- **The applications scope:** `lens.sh 4` keeps 5 deleted mappings over 4 re-indexes.
- **The Dash:** "термин" and the misspelt "тирминал" both find Terminal (screenshots in logs/).
- These are the same results as the +unity1 publication check (UNITY-20261008-013, logs/07).
- logs/04 also records the commands of the rerun of setup step 3 and the builder-side index step.
- `tested_build`: this_build.

## Verification (independent Verifier, 2026-10-10): PASS

The Verifier did not make the rebuild. Review status: INDEPENDENTLY_REPRODUCED. It reran the build
comparisons and the scripted target checks on target2 itself.

- **The source change:**
  - `3da4d89` is the published +unity1 commit, the `source_commit` of UNITY-20261008-013's publish record.
  - `git diff --name-status 3da4d89 63c6950` shows only `M debian/changelog`, 6 added lines.
  - `dpkg-parsechangelog` gives the +unity2 entry: resolute, NeiroNext, a UTC date, the stated text.
  - The commit has author and committer NeiroNext, and no `Signed-off-by` anywhere.
- **Provenance:**
  - the manifest's commit and tree equal git, and all 11 artifact sha256 and the log's equal the files;
  - `dpkg-source -x` of the `.dsc` equals `git archive 63c6950` (107 files, modes included);
  - `dscverify` validates every file;
  - the orig tarball equals the published one;
  - the chroot block, the build command and the sbuild configuration hash equal +unity1's, and the
    `Installed-Build-Depends` of the two `.buildinfo` files are identical.
- **Tests:** 18 of 18 pass, the same 18 tests as +unity1.
- **Binaries:**
  - `payload.sh` and `elfcmp.sh` rerun give byte-identical outputs to logs/02 and logs/03;
  - mutation tests confirm that `elfcmp.sh` reads non-allocated sections, but not the headers;
  - `zerocmp.py` closes that gap: both stripped files are identical as whole files with the three notes
    zeroed (logs/05);
  - the `.ddeb` debug information is identical once the version is normalised.
- **target2:**
  - +unity2 is installed and the candidate, `dpkg -V` is clean, and the repository `.deb` files and the
    installed library equal the build;
  - only hud-service and the applications scope map libcolumbus, both the installed inode, with 0 deleted
    libraries;
  - its rerun of `target-check.sh`: the HUD gives 0 → 3 → 0, `leak.sh` 0 at all 6 steps, the lens a constant
    5 over 4 re-indexes;
  - no test process was left running.
- **The card** matches logs/04 and the -013 logs/07 pattern.

Remarks (taken into the card above):

1. The `.ddeb` files differ by more than build-id names (version paths in `.debug_line_str`, LTO symbol
   suffixes), all from the version and debug-only.
2. `elfcmp.sh` does not cover headers or padding; `zerocmp.py` does.
3. `payload.sh` compares file lists by permissions and name only; sizes and link targets were checked
   separately.
4. The `_amd64.changes` lists only the binaries and the `.buildinfo`. The build is `all amd64`, as +unity1's
   was. The `.dsc` and its files reach the repository through the manifest, as in every earlier publication.
5. Wording ("the same results as") and the logging of the step-3 rerun, both corrected.
6. target2 is left dirty: +unity2 from the file repository. It is restored to Clean-2 before the publication
   check.

Not run: the Dash search (the Verifier used the screenshots); the setup (no restore or package change, by its
brief); a rebuild; the signer, the gate and the publication.

## Known gaps

| gap | where it is covered |
|---|---|
| The `.ddeb` debug files are not byte-identical to +unity1's (version strings in paths and LTO symbol names). | debug-only; compared with the version normalised |
| The archive signer itself is what this publication tests; if its routine policy does not sign, the publisher waits for May on the signer console. | ENGINEERING-PROCESS section 6 (signer mode); the outcome goes into the publication record |
| NOT_APPLICABLE + MECHANICAL_PACKAGING_ONLY cannot reach a gate in the current tools, so this task carries a real Verifier PASS. | UNITY-20261010-002 |
