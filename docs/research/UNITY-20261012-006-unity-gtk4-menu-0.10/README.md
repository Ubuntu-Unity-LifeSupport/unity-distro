# UNITY-20261012-006: unity-gtk4-menu 0.10 (preload by path)

Agent A, target `target-desktop`. Released together with UNITY-20261012-005
(gtk-nocsd 4.8-1+unity4); one session test covers both.

## What is fixed

| package | version | change |
|---|---|---|
| unity-gtk4-menu | 0.10 | Commit `aa00846` on the published 0.9 (`7ce9092`), branch `a/UNITY-20261012-006`. |

- The library is preloaded by path, `/usr/$LIB/libunity-gtk4-menu.so.0`, in
  `/usr/lib/environment.d/60-unity-gtk4-menu.conf` (written `$$LIB` there).
  The dynamic loader expands `$LIB` to the multiarch directory. The library
  no longer carries the setuid bit (mode 0644); the matching lintian
  overrides are removed. README describes the path form.
- No change to `debian/control`: dependencies and the binary package are
  unchanged.
- After the upgrade, log out and back in.

## Build

Built with `scripts/build_sbuild.py` from `aa00846`, chroot snapshot
T=20261008T083223Z. Lintian: no error. `dpkg -c`:
`libunity-gtk4-menu.so.0` is `-rw-r--r--`. The manifest is in `build/`.

## Checks

- **Target** (`gate/target-test.txt`): see UNITY-20261012-005; the session
  test covers both packages. GTK4 applications show their header bar menu
  in the panel as before; the library is loaded by path in session
  processes; privileged programs print nothing after a relogin.

## Verification

- Target test before publication: PASS (`gate/target-test.txt`).
- Independent verification: PASS (the Verifier reviewed the diffs against the
  approved design, ran the script tests and the environment.d generator, and
  checked the build records and the target record against its raw outputs
  and screenshots).

## Publication

- **Database backup:** `/home/claude/backups/UNITY-20261012-006-20261013T002830Z`.
  20 files, complete, equal to live; list sha256
  `73b19a8f32e5941de0feb4cf37c72947de68ea564a981c8509955853cc5bf430`.
- **Repository:** 3 records added to `unity-resolute` (the source, 1 .deb
  and 1 .ddeb). The sha256 of every pool file matches the build manifest.
- **Snapshot:** `unity-resolute-20261012-006`, which is the live
  `unity-resolute-20261012-005` (gtk-nocsd +unity4) plus these 3 records
  (`gate/snapshot-diff.txt`).
- **Version safety:** SAFE (`gate/version-check.json`,
  `gate/version-safety.json`).
- **Peer notice:** agent B, ACK.

## Release note

Log out and back in after the upgrade. Until then, privileged programs
started from the running session print one dynamic loader message per
library listed in the session's earlier value; the programs run normally.
