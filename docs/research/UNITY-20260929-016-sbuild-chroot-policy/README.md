# UNITY-20260929-016: sbuild chroot policy

Agent A. From UNITY-20260927-041 (B noticed the change). Blocks the next
gated builds (indicator-keyboard, nux, hud, ...).

## 1. What happened

- DECISIONS 2026-09-22 ("sbuild runs in unshare mode"): builds use sbuild's
  unshare mode with `~/.cache/sbuild/resolute-amd64.tar.zst`, made by
  `mmdebstrap --variant=buildd`. The record gives neither the mirror, the
  suites nor a refresh rule.
- That tarball (mtime 2026-09-22 17:46:45Z, 141950002 bytes) has one
  source: `deb http://de.archive.ubuntu.com/ubuntu resolute main universe
  restricted multiverse` - the release pocket only, no -updates, no
  -security.
- sbuild 0.91.2 (`Sbuild/ChrootUnshare.pm`): a tarball older than
  `$unshare_mmdebstrap_max_age` (default 604800 s, "one week like the
  buildds") is not used. With `$unshare_mmdebstrap_auto_create` on (the
  default) and `$unshare_mmdebstrap_keep_tarball` off (the default), every
  build then runs
  `mmdebstrap --variant=buildd --arch=amd64 --skip=output/mknod --format=tar resolute - --components=main,universe`
  and unpacks it from stdin; nothing is kept. That chroot uses mmdebstrap's
  default Ubuntu sources: `archive.ubuntu.com` resolute and
  resolute-updates, `security.ubuntu.com` resolute-security, components
  main and universe only.
- The switch happened at 2026-09-29 17:46Z. Builds since then that got an
  on-demand chroot (log line "Existing chroot tarball is too old"):
  UNITY-20260927-041's gated calamares-settings-ubuntu +unity3 build
  (published) and UNITY-20260929-014's test build Q1 (tiny013, not
  published). UNITY-20260927-040's gated build (17:19-17:36Z) and every
  earlier one used the tarball.
- Nothing records which chroot a build used, except the sbuild log. The
  `.buildinfo` lists Installed-Build-Depends, but not the sources or the
  chroot.
- Users' sources (target-desktop): `de.archive.ubuntu.com` resolute,
  -updates, -backports; `security.ubuntu.com` resolute-security; components
  main, universe, restricted, multiverse.

So today's builds are neither what users run against (on the tarball: no
-updates/-security) nor reproducible (on-demand: a new, unrecorded chroot per
build), and the switch between the two was silent.

## 2. Existing fix

Our own infrastructure. Nothing on the board or in DECISIONS covers the
chroot's sources or refresh; `build_sbuild.py` passes no chroot option and
records no chroot. sbuild offers the pieces: `SBUILD_CONFIG` (a config file
read after the user's), `--chroot=<tarball>`, `$unshare_mmdebstrap_max_age`
(negative = never too old), `$unshare_mmdebstrap_auto_create` (0 = never
create on demand). `NOT_FIXED`.

## 3. First proposal (superseded by section 5)

P1. **One explicit, recorded tarball per refresh.** A new
`scripts/sbuild_chroot.py create` runs mmdebstrap with explicit sources,
matching users' pockets:
`resolute`, `resolute-updates` (`de.archive.ubuntu.com`, the mirror target
and the old tarball use) and `resolute-security` (`security.ubuntu.com`);
components main, universe, restricted, multiverse; no -backports,
no -proposed. It writes `~/.cache/sbuild/chroots/resolute-amd64-<UTC>.tar.zst`
and a sidecar `.json`: sha256, size, created_at, mmdebstrap version and
argv, the sources file, each suite's `InRelease` Date from inside the
tarball, and the chroot's package list (`dpkg-query -W`). Old tarballs are
kept (a published manifest may name one).

P2. **No silent chroot.** `build_sbuild.py` runs sbuild with
`SBUILD_CONFIG=<repo>/build/sbuild-config.pl` (auto_create 0, max_age -1:
sbuild neither creates a chroot nor refuses the tarball for age) and
`--chroot=<the current tarball>`. Before sbuild: the tarball must exist,
have its sidecar, and match the sidecar's sha256. After: the tarball is
hashed again, and the log must show `Unpacking <that tarball>` and none of
"too old", "Creating new chroot", "Unpacking tarball from STDIN"; otherwise
refuse (exit 2, no manifest).

P3. **Recorded in the manifest.** A `chroot` key: tarball file name,
sha256, created_at, sources, sidecar sha256. `create_release_gate.py` and
`publish_aptly.py` are not changed (the chroot is build provenance, not a
publication input).

P4. **Refresh rule.** The current tarball is the newest in
`chroots/`. It is refreshed with `sbuild_chroot.py create` (i) before a
gated build when it is older than 7 days, and (ii) whenever the tester
build and the gated build of one task would otherwise differ: the gated
build uses the same tarball (sha256) as the build that was tested on
target, or the test is repeated. `build_sbuild.py` refuses a tarball older
than 7 days unless `--allow-old-chroot` is given (for rebuilding an old
release byte for byte). The sbuild default path
`~/.cache/sbuild/resolute-amd64.tar.zst` is left as it is (history of the
builds before this task).

P5. **The -041 publication.** It was built on an on-demand chroot with
-updates/-security, main+universe only. Its payload is published and
verified; this task records it (DECISIONS) and does not rebuild it.

Rejected so far:
- `$unshare_mmdebstrap_keep_tarball = 1` (sbuild refreshes on its own
  schedule, with main+universe only and mmdebstrap's mirror; a refresh is
  still silent).
- Release pocket only (the old tarball): our packages run against -updates
  and -security; the Launchpad builds for resolute-updates build against
  release + security + updates.
- `max_age -1` on the old tarball alone: reproducible, but frozen at
  2026-09-22 and without -updates/-security.

Open for May (through the coordinator), if the Challenger agrees: building
against -updates/-security is a change of what every future package is
built against.

## 4. Design review 1: REVISE

Temporary Design Challenger (read-only subagent). Its findings, checked
here against sbuild 0.91.2:

- **Pinning the tarball does not pin the build.** sbuild's defaults are
  `$apt_update = 1` and `$apt_distupgrade = 1` (`Sbuild/Conf.pm`): every
  build runs `apt-get update` and `dist-upgrade` in the chroot against the
  chroot's sources. With the old release-only tarball that was a no-op (the
  -040 log: "0 upgraded"). With -updates/-security, two builds on the same
  tarball sha256 get different packages.
- **The tarball carries no apt lists.** `var/lib/apt/lists/` holds only
  `lock` and `partial/`; mmdebstrap cleans them, so no InRelease Date can be
  read from it afterwards.
- `--chroot=<path>` works in unshare mode, and an explicit path is never
  "too old" (`ChrootUnshare::chroot_tarball_if_too_old`) and never
  auto-created. So `max_age` is a no-op for it. sbuild's real on-demand line
  is `I: Creating chroot on-demand`, and a bare `Unpacking` also matches
  dpkg's `Unpacking mount (...)`.
- Side finding: `~/.sbuildrc` is not read, because
  `~/.config/sbuild/config.pl` exists. Its `parallel=4` has not applied
  since 2026-09-23 (follow-up).
- The Launchpad statement in the first draft was imprecise: SRUs build in
  -proposed with -proposed enabled, and a universe source builds against
  main, restricted and universe, not multiverse.
- The -041 handling holds: its log and `.buildinfo` record what it used.
  UNITY-20260929-014's Q1 was also on an on-demand chroot (a test build, not
  published).

## 5. Proposal, revised

**R1. Reproducibility model.** Two models; the choice (with the pockets) is
May's:

- **(B, recommended) Pinned archive snapshot.** Sources in both the tarball
  and the build are `https://snapshot.ubuntu.com/ubuntu/<T>` for
  `resolute`, `resolute-updates` and `resolute-security` (reachable: the
  resolute InRelease for 20260929T000000Z answers 200). `<T>` is chosen at
  each refresh and recorded. The build's `apt-get update`/`dist-upgrade`
  then sees the same archive state as the tarball, so the same tarball
  gives the same build dependencies, now and later. A rebuild of an old
  release needs only its tarball (or its `<T>`). Cost: builds depend on
  snapshot.ubuntu.com, which is slower than a mirror.
- **(A) Live pockets, the `.buildinfo` as the record.** Sources are the live
  mirror (`de.archive.ubuntu.com`, `security.ubuntu.com`). The tarball is
  only a base, and `dist-upgrade` moves each build to that day's -updates
  and -security. What a build was built against is its `.buildinfo`
  Installed-Build-Depends. The gated build must match the tested build's
  Installed-Build-Depends, or the target test is repeated. An old release
  cannot be rebuilt byte for byte (superseded versions leave the index).

**R2. Components.** main, universe, restricted, multiverse (as users have
them), or main, universe, restricted (as Launchpad builds a universe
source). Recommended: without multiverse, so that a build dependency cannot
resolve from a component Launchpad would not use. Also May's choice.

**R3. Creating a tarball.** `scripts/sbuild_chroot.py create` fixes the
mmdebstrap argv (sources per R1 and R2, `--variant=buildd`,
`--skip=cleanup/apt/lists` or a hook that saves each suite's InRelease
Date). It writes `~/.cache/sbuild/chroots/resolute-amd64-<UTC>.tar.zst`
and a sidecar `.json` with the argv, the sources, the InRelease Dates, the
package list and the sha256.

**R4. Building.** `build_sbuild.py` resolves the current tarball to an
absolute path (no symlink) and passes `--chroot-mode=unshare
--chroot=<path>`, with `SBUILD_CONFIG=<repo>/build/sbuild-config.pl`
(`$unshare_mmdebstrap_auto_create = 0` as a guard; `$apt_distupgrade`
unchanged; `DEB_BUILD_OPTIONS` parallel set there once the follow-up
decides it). It does not trust the sidecar: it hashes the tarball before
and after, and reads `./etc/apt/sources.list` from it. The log must contain
`^I: Unpacking <path> to ` and none of `Creating chroot on-demand` or
`Creating new chroot tarball`; otherwise refuse with exit 2 and no manifest.
The manifest gets a `chroot` key: file, sha256, sources from the tarball,
the sidecar's sha256 and InRelease Dates, and the build log's `Get: ...
InRelease` lines.

**R5. Refresh and retention.** Under (B): a new tarball (new `<T>`) when a
task needs a newer archive state, and at least before a gated build whose
current `<T>` is more than 7 days old. The tested and gated builds of one
task use the same tarball. Under (A): refresh weekly so dist-upgrade stays
small, and compare Installed-Build-Depends between the tested and gated
builds. Either way: keep every tarball named by a published manifest,
prune the rest, and leave the old `~/.cache/sbuild/resolute-amd64.tar.zst`
as the record of the builds up to 2026-09-29.

**R6. The -041 publication and the -014 Q1 run** are recorded in DECISIONS
as built on an on-demand chroot (live archive.ubuntu.com resolute, -updates
and -security, main and universe); no rebuild.

**Tests.** Unit tests with log fixtures (-040 tarball, -041 on-demand,
-014 Q1):
- a missing tarball fails with no manifest;
- a sha256 change during the build fails;
- the on-demand log is refused;
- a dpkg `Unpacking` line does not satisfy the check;
- the manifest's `chroot` key is present and correct;
- `SBUILD_CONFIG` values are applied (sbuild's log).

Plus one real small build per model chosen.

## 6. May's decisions and the design to implement

May, through the coordinator, 2026-09-29:
- Model (B): the tarball and the build both use
  `https://snapshot.ubuntu.com/ubuntu/<T>`, and `<T>` is recorded at each
  refresh.
- Pockets: release, -updates and -security.
- Components: main, universe and restricted, without multiverse.
- Plus `--chroot=<absolute path>`, and a refusal when the log shows
  "Creating chroot on-demand".

The follow-up for `~/.sbuildrc` is UNITY-20260929-017.

The snapshot service, checked 2026-09-29: for `<T>` = 20260929T000000Z,
`dists/resolute`, `-updates` and `-security` all answer 200. The InRelease
files carry no Valid-Until. `<T>` resolves to the latest publication before
it (-updates Date 28 Sep 21:58 UTC). One request for the release pocket
timed out and a retry answered in 1.3 s.

**D1. `scripts/sbuild_chroot.py create --snapshot <T>`** (default: now,
UTC, `YYYYMMDDTHHMMSSZ`; `--series resolute`, `--arch amd64`):
- Fetches `dists/<suite>/InRelease` of the three suites from the snapshot
  and records each Date and sha256. It refuses if any is missing.
- Runs `mmdebstrap --variant=buildd --arch=amd64 --skip=output/mknod
  --components=main,universe,restricted --aptopt='Acquire::Retries "5"'
  resolute <tmp>.tar.zst` with three explicit
  `deb https://snapshot.ubuntu.com/ubuntu/<T> <suite> main universe restricted`
  lines. These become the chroot's `/etc/apt/sources.list`.
- Renames the result to `~/.cache/sbuild/chroots/<series>-<arch>-<T>.tar.zst`
  and writes a sidecar `<same>.json`. The sidecar holds the schema, series,
  arch, `<T>`, the sources lines, the InRelease Dates and sha256s, the
  mmdebstrap version and argv, created_at, and the tarball's name, sha256,
  size and package list (read from `var/lib/dpkg/status` in the tarball).
- It refuses to overwrite an existing tarball.

**D2. `build/sbuild-config.pl`**, passed as `SBUILD_CONFIG`, sets
`$unshare_mmdebstrap_auto_create = 0` as a guard. An explicit `--chroot`
path is never auto-created anyway.

**D3. `build_sbuild.py`.**
- `--chroot-tarball PATH`. The default is the newest `<series>-<arch>-*.tar.zst`
  in `~/.cache/sbuild/chroots/` that has a sidecar.
- Before sbuild:
  - The path is resolved to an absolute path.
  - The sidecar must exist, and its sha256 must match the tarball.
  - `./etc/apt/sources.list` inside the tarball must be exactly the
    sidecar's lines. Those lines must be the three pockets of the target
    series on `snapshot.ubuntu.com/ubuntu/<T>` with main, universe and
    restricted.
  - `<T>` must be no more than 7 days old, unless `--allow-old-chroot` is
    given; the manifest records whether it was.
- sbuild gets `--chroot-mode=unshare --chroot=<abs path>` and runs with
  `SBUILD_CONFIG=<repo>/build/sbuild-config.pl`.
- After sbuild, refuse with exit 2 and no manifest if any of these fails:
  - The tarball's sha256 must be unchanged.
  - The log must contain `I: Unpacking <abs path> to `.
  - The log must not contain `Creating chroot on-demand`,
    `Creating new chroot tarball` or `Unpacking tarball from STDIN`.
  - Every `Get:` line fetching over http(s) must be under
    `https://snapshot.ubuntu.com/ubuntu/<T>/`. Local `file:` and `copy:`
    lines, from sbuild's own archive of the build dependencies, are allowed.
- The manifest gets a `chroot` key:
  - the tarball's path, sha256 and size;
  - the sidecar's path and sha256;
  - `<T>`, the sources and the InRelease Dates;
  - `allow_old_chroot`;
  - the log's `InRelease` Get lines.

**D4. Refresh and retention.**
- A new tarball, with a new `<T>`, is created with `sbuild_chroot.py
  create` when the current one is more than 7 days old; `build_sbuild`
  refuses such a tarball, as in D3. A new tarball is also created whenever
  a task needs a newer archive state.
- The test build and the gated build of one task should name the same
  tarball. If they do not, their `.buildinfo` Installed-Build-Depends are
  compared, and the target test is repeated on any difference.
- Every tarball named by a committed manifest is kept. Others may be
  deleted by hand.
- The old `~/.cache/sbuild/resolute-amd64.tar.zst` stays as the record of
  the builds up to 2026-09-29.

**D5. Records.**
- DECISIONS gets the policy.
- DECISIONS gets a separate entry, now, via `append_record.py`: -041 and
  -014's Q1 were built on sbuild's on-demand chroot, with no rebuild.
- ENGINEERING-PROCESS section 6 gets the build step with the tarball.

**Tests.**
- Unit tests with a small fake tarball and sidecar, using the sbuild stub:
  - a missing tarball, a missing sidecar, a sha256 mismatch, a sources
    mismatch, a foreign mirror, and multiverse or -proposed in the sources
    are each refused before sbuild;
  - an old `<T>` is refused without `--allow-old-chroot`;
  - the log checks work: an on-demand line (with the -041 log as a
    fixture), no Unpacking line, a dpkg `Unpacking` line only, a non-snapshot
    Get line, and a tarball changed during the build;
  - the manifest's `chroot` key.
- A real `sbuild_chroot.py create`, then one real build of tiny013 and one
  of a real package, checking that `dist-upgrade` is a no-op ("0 upgraded").

## 7. Design review 2: REVISE, changes applied

The Challenger's round 2 on section 6 asked for five changes:

1. **CA certificates.** The snapshot answers only over https, and the buildd
   variant has no CA certificates, so sbuild's `apt-get update` inside the
   chroot would fail. The fix is `--include=ca-certificates`. The
   `--components` option only applies to bare mirror arguments, so it was
   dropped; the components are in the deb lines.
2. **Sources comparison.** mmdebstrap separates its `sources.list` entries
   with blank lines, so only the non-empty lines are compared. The tarball's
   `sources.list.d/` must be empty.
3. **URI check.** The check applies to every apt `Get:`, `Hit:`, `Ign:` and
   `Err:` line, not only `Get:`.
4. **Same tarball, as a requirement.** The test build and the gated build
   use the same tarball (a must, not a should). `--tested-with <manifest>`
   enforces it and is recorded. `--allow-old-chroot` is sanctioned for a
   gated build on the tested tarball.
5. **Tests.** As listed below.

It also found that nothing else in sbuild adds a non-snapshot source: only
the `copy:`/`file:` archives of the build dependencies, and deb-src lines
that reuse the existing URIs.

## 8. Implementation and validation

Code `ca84422` (branch `a/UNITY-20260929-016`):

- `scripts/sbuild_chroot.py`: `create`, plus the functions `check_tarball`,
  `check_log` and `current_tarball`.
- `build/sbuild-config.pl`: `$unshare_mmdebstrap_auto_create = 0`.
- `scripts/build_sbuild.py`: `--chroot-tarball`, `--allow-old-chroot` and
  `--tested-with`. It checks the tarball before sbuild, passes
  `--chroot-mode=unshare --chroot=<path>` with `SBUILD_CONFIG`, checks the
  tarball and the log after sbuild, and writes the manifest's `chroot` key.
- `docs/ENGINEERING-PROCESS.md`: the build chroot, in section 6.

Tests:

- `test_sbuild_chroot.py`, with fixtures in `chroot_fixtures.py`: 8 tests.
  The tarball checks cover multiverse, -proposed, the live mirror, another
  snapshot, a `sources.list.d` file, a missing sidecar, and a sidecar sha256,
  series or sources mismatch, each refused. They also cover the age limit and
  its override, a symlink, a relative path and the name. The log checks run
  on real line forms from -040 and -041: an on-demand chroot, no unpack line,
  a dpkg `Unpacking` line only, another tarball, a prefix match, a foreign
  `Get:` or `Hit:` line, another snapshot, and a `.evil` suffix on the
  snapshot path are each refused.
- `test_build_sbuild.py`: 5 new tests. They check the manifest `chroot` key
  and that `SBUILD_CONFIG` reaches sbuild; refusals before sbuild (missing,
  no sidecar, live mirror, old, symlink), which run no sbuild and leave the
  output empty; refusals after sbuild (on-demand, not unpacked, foreign
  mirror, tarball changed); the recorded `--allow-old-chroot`; and
  `--tested-with` with the same and with another tarball. The existing tests
  now pass a fixture tarball.
- On main's `build_sbuild.py` the build tests fail
  (`runs/new-tests-on-main-21b98ed.txt`, 42 failures). Every test passes
  `--chroot-tarball`, which main does not know. The new refusal tests assert
  their own messages, so an argument error cannot satisfy them.
- On the branch: full suite 213 OK (1 skipped).

Real runs (`tools/run-real.sh`, `runs/run-real.log`, `runs/run-real-s4.txt`):

- **S1** `sbuild_chroot.py create --snapshot 20260929T201245Z`: exit 0 in
  about 2 minutes, a 143 MB tarball with 126 packages, including
  `ca-certificates`. The InRelease Dates are resolute 23 Apr, -updates
  29 Sep 19:18 and -security 29 Sep 18:35. Sidecar:
  `runs/resolute-amd64-20260929T201245Z.json`.
- **S2** tiny013 on it: exit 0. sbuild unpacked exactly this tarball and
  fetched the three InRelease files over https from the snapshot. The
  dist-upgrade shows "0 upgraded, 0 newly installed". Manifest:
  `runs/s2-tiny013-build-manifest.json`.
- **S3** unity `7b0eca27` with our nux from the pool, on the same tarball:
  exit 0, `Status: successful`, "0 upgraded" in the dist-upgrade. The
  `file:` and `copy:` archives are accepted. Manifest:
  `runs/s3-unity-build-manifest.json`; log: `runs/s3-unity-sbuild.log.xz`.
  Both manifests name tarball sha256 `d48b7864...` and snapshot
  `20260929T201245Z`.
- **S4** the old `~/.cache/sbuild/resolute-amd64.tar.zst`: refused before
  sbuild (not a snapshot tarball); exit 2, output empty.
