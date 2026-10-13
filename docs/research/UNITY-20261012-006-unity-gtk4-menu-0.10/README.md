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
