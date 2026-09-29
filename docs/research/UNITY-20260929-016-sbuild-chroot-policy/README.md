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
