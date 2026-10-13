# UNITY-20261012-005: gtk-nocsd 4.8-1+unity4 (preload by path)

Agent A, target `target-desktop`. Released together with UNITY-20261012-006
(unity-gtk4-menu 0.10); one session test covers both.

## What is fixed

| package | version | change |
|---|---|---|
| gtk-nocsd | 4.8-1+unity4 | Commit `a4ec25e` on the published +unity3 (`a2a0747`), branch `a/UNITY-20261012-005`. |

- The library is preloaded by path, `/usr/$LIB/libgtk-nocsd.so.0`, in
  `/usr/lib/environment.d/50-gtk-nocsd.conf` (written `$$LIB` there) and
  in `/etc/X11/Xsession.d/51gtk-nocsd`. The dynamic loader expands `$LIB`
  to the multiarch directory. The library no longer carries the setuid
  bit (mode 0644); the matching lintian overrides are removed.
- `51gtk-nocsd`:
  - separates LD_PRELOAD entries with `:` only (spaces, tabs and newlines in
    an inherited value broke the session start);
  - writes the bare names of earlier releases (`libgtk-nocsd.so.0`,
    `libunity-gtk4-menu.so.0`) as paths;
  - reads the systemd user manager's value in the form `systemctl` prints it;
  - adds nothing when an `environment.d/50-gtk-nocsd.conf` in `/etc`,
    `/run`, `/usr/local/lib` or the user's configuration directory turns
    gtk-nocsd off.
- `debian/test-51gtk-nocsd.sh` runs the script at build time under dash and
  bash, with and without `set -eu` (24 cases each).
- No change to `debian/control`: dependencies and the binary packages are
  unchanged.
- After the upgrade, log out and back in.

## Build

Built with `scripts/build_sbuild.py` from `a4ec25e`, chroot snapshot
T=20261008T083223Z; the upstream tarball is the one already published with
+unity3 (sha256 `2be0214c...`). The script test: 96 PASS, 0 FAIL. Lintian:
no error. `dpkg -c`: `libgtk-nocsd.so.0` is `-rw-r--r--`. The manifest is
in `build/`.

## Checks

- **Target** (`gate/target-test.txt`), published configuration plus these
  builds of gtk-nocsd and unity-gtk4-menu:
  - after the upgrade, until the next login, privileged programs print one
    loader message per library of the earlier session value;
  - after a relogin (with the user manager stopped, and with it kept
    alive), the session and the user manager have the path form, the
    libraries are loaded in session processes, and privileged programs
    print nothing;
  - client-side decorations removed and the global menu present as before;
  - a value with spaces, and the opt-out file, behave as described above.

## Verification

- Target test before publication: PASS (`gate/target-test.txt`).
- Check on the target after publication: PASS. Published 2026-10-13
  00:08:28Z as `unity-resolute-20261012-005`; the target updated from the
  live repository, cold boot: the session has the path form, both
  libraries are loaded, privileged programs print nothing
  (`gate/target-verification.txt`). The first boot ended at start with an
  abort in libcompizconfig, recorded there; the second boot was normal.
- Independent verification: PASS (the Verifier reviewed the diffs against the
  approved design, ran the script tests and the environment.d generator, and
  checked the build records and the target record against its raw outputs
  and screenshots).

## Publication

- **Database backup:** `/home/claude/backups/UNITY-20261012-005-20261013T000344Z`.
  20 files, complete, equal to live; list sha256
  `4ef73d9ac677f11c2e4d2d1d972035c7b0cd0448bd6009275315a64cbbdd74f1`.
- **Repository:** 5 records added to `unity-resolute` (the source, 3 .deb
  and 1 .ddeb). The sha256 of every pool file matches the build manifest;
  the upstream tarball is the pool file already published with +unity3.
- **Snapshot:** `unity-resolute-20261012-005`, which is the live
  `unity-resolute-20261009-003` plus these 5 records
  (`gate/snapshot-diff.txt`).
- **Version safety:** SAFE (`gate/version-check.json`,
  `gate/version-safety.json`).
- **Peer notice:** agent B, ACK.

## Release note

Log out and back in after the upgrade. Until then, privileged programs
started from the running session print one dynamic loader message per
library listed in the session's earlier value; the programs run normally.
