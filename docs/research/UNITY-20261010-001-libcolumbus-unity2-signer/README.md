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
The `.ddeb` files differ for the same reason: their file names are the new build-ids.

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
- These are the results of the +unity1 publication check (UNITY-20261008-013, logs/07).
- `tested_build`: this_build.
