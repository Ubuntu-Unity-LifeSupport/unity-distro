# UNITY-20260927-021 - independent verification

## Round 1 (2026-09-29, ephemeral Verifier; card 065d128, source c03daf48)

Verdict: **INCOMPLETE**, `REVIEWED`. No finding values.

Confirmed for the Ubuntu Unity binaries:

- Source: the diff vs the archive c6997017 touches only
  `common/basicwallpaper/main.cpp` (unchanged since b6b546b) and +19 lines of
  `debian/changelog`. The archive changelog's 1491 lines are byte-identical,
  and the +unity2 trailer is UTC. The `.tar.xz` equals `git archive c03daf4`
  apart from `.gitignore`.
- Manifest: the tree hash equals `c03daf4^{tree}`; all 10 artifact hashes
  and the log hash match; sbuild `Status: successful` (the package has no
  tests).
- Regression: logs/06 (gated deb, basicwallpaper 077f7c36, 3/3) vs logs/01
  (archive cdd40699, fails) is a valid demonstration. It runs in an
  Xvfb/xfwm4 chroot, not a cold OEM boot.
- File lists and controls of -ubuntu-unity/-common/-common-data equal
  +unity1 apart from the version pins; the oemconfig list is identical.
- dpkg ordering: +unity1 < +unity2 < +unity3 (-041 descends from c03daf4).

Missing proof: calamares-settings-lubuntu/-kubuntu +unity2 ship the patched
basicwallpaper and are new in our repository. Their behaviour is unmeasured.
To close it: a measurement, or a recorded owner decision on publishing
them.

## Round 2 (2026-09-29, same Verifier; card f8fd263)

Verdict: **PASS** (PATCH_CORRECT), `REVIEWED`.

May's decision is recorded in the README and the evidence
(`publication_scope_decision`): publish all 6 binaries, knowing the
Lubuntu/Kubuntu basicwallpaper is unmeasured and that
1:26.04.12ubuntuN SRUs for them will be shadowed. It was confirmed a second
time. This closes the round-1 INCOMPLETE. Nothing verified in round 1 has
changed.

Limits: the Verifier checked C's record of the decision, not the decision
itself. Lubuntu/Kubuntu behaviour stays with UNITY-20260927-044.

## Round 3 (2026-09-29, same Verifier; build-r2, branch c79ddfb)

Verdict: **PASS** (PATCH_CORRECT), `REVIEWED`. The rebuild does not change
what ships.

- build-r2 manifest:
  - source_repo is `packages/calamares-settings-ubuntu` in the worktree,
    commit c03daf48, tree d4fb3f58;
  - origin (GitHub) `b/UNITY-20260927-021` contains it;
  - all 10 artifact hashes and the log hash match;
  - `Status: successful`.
- Cause of the hash difference (it corrects logs/08):
  - the format is 3.0 (native);
  - .dsc/.tar.xz differ only by the tarball's top directory (`021-push/` vs
    `calamares-settings-ubuntu/`), with identical unpacked sources;
  - -ubuntu-unity/-kubuntu/-lubuntu differ only by the file dates inside
    `oemconfig.tar.gz`, which the Makefile packs at build time. Contents,
    modes and owners are identical, basicwallpaper 077f7c36 included;
  - -common, -common-data and -dbgsym are byte-identical.
- logs/09 and logs/10 hold for r2.
- All 8 r2 files are in the pool. The 5 first-build files remain.
  `public/pool` still has only the +unity1 debs.

Missing proof it named: what snapshot -021-r2 contains. Closed by B:
logs/13, `aptly snapshot search` on unity-resolute-20260927-021-r2. The
six +unity2 binaries have exactly the r2 manifest's sha256, so the
first-build files are orphans. The source record is checked by the
publisher through Checksums-Sha256.

Remark: oemconfig.tar.gz changes with every rebuild of the same commit.
