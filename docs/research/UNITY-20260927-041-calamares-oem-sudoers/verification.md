# UNITY-20260927-041 - independent verification

## Round 1 (2026-09-29, ephemeral Verifier subagent; gated build of 221c691, branch 315d97d)

Verdict: **PASS** (PATCH_CORRECT). Review status: `INDEPENDENTLY_REPRODUCED`.
The Verifier reproduced the modes in the shipped tarballs itself. The
visudo -c results come from logs/03 and logs/07.

What the Verifier checked:

- **Defect in the archive.** `apt-get download
  calamares-settings-ubuntu-unity=1:26.04.12` gives
  `ubuntuunity/oemconfig/etc/sudoers.oem` `-rw-r--r-- root/root`. Kubuntu
  and Lubuntu are `-r--------`.
- **Cause.** Makefile line 51 at c03daf4 chmods Kubuntu's copy, whose
  tarball is already built at line 46. The Unity copy keeps git's 0644.
- **Diff.** `git diff c03daf4 221c691` touches line 51 and the changelog
  only. The remote branch is at 221c691. Tree e1c3eec equals the manifest.
  The unpacked .dsc equals `git archive 221c691`, apart from `.gitignore`.
- **Fix.** In the gated -ubuntu-unity deb, sudoers.oem is
  `-r--r----- root/root`, 1762 bytes, sha256 d0a025d4…, the same content as
  before.
- **Unchanged otherwise:**
  - the three tarballs match +unity2 apart from that entry and
    basicwallpaper;
  - the file lists of all six binaries match, apart from the dbgsym build
    IDs;
  - the published +unity2 in the pool equals build-r2;
  - all 11 manifest files match their sha256 and size;
  - the changelog has 96 entries, +unity3 on top, with a UTC trailer.
- **basicwallpaper.** Its code sections are identical. The only
  differences are the build ID, the package note and the debug path strings.
- **Mode and layer.** 0440 is right: visudo -c accepts only 0440 (logs/03),
  and `/etc/sudoers` on builder is 440. The Makefile is the only place that
  sets this mode, and git keeps only the executable bit. oemfinish
  restores `/etc/sudoers.orig` and is not affected.

Remarks (non-blocking):

- **Build environment.** +unity3 was built with resolute-updates/-security,
  +unity2 with the release pocket only. `-common`'s `snap-seed-glue-emb`
  is statically built against snapd 2.76.3+ubuntu26.04 instead of
  2.74.1+ubuntu26.04.4, and it grew by 219 kB.
  - The card now records this (README, "Gated build").
  - The target check covers the installer's snap seeding step.
- **Other flavours.** Kubuntu and Lubuntu ship 0400, which visudo -c also
  rejects. This is out of scope and recorded as such.

Not checked:

- The live OEM path with the published build. That is the target
  verification.
- visudo -c on the gated artifacts; logs/07 covers the preliminary build.
- What the snapd change does inside snap-seed-glue-emb.
