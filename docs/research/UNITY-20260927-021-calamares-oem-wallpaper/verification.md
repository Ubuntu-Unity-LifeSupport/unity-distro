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
