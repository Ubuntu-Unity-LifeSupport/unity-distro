# Decisions

Append-only log. Record what was chosen, why, and what was tried and rejected -
otherwise the next session repeats the same dead ends.

---

## 2026-09-22 - sbuild runs in unshare mode, not schroot

**Decision.** Build in `sbuild`'s unshare mode, with a tarball at
`~/.cache/sbuild/resolute-amd64.tar.zst` built by `mmdebstrap --variant=buildd`.

**Why.** sbuild 0.91 in Ubuntu 26.04 defaults to unshare mode. It needs no root
and no `sbuild` group membership, which removes a whole class of setup problems.

**What was tried first and failed.** `sbuild-createchroot` was used to build a
classic schroot at `/srv/chroot/resolute-amd64-sbuild`. Every build then died
with `E: Error creating chroot session`, for two independent reasons:

1. sbuild was looking for an unshare tarball and found none
   (`I: No tarballs found in /home/claude/.cache/sbuild`).
2. Wrapping the call to pick up the `sbuild` group (`sudo -u claude -g sbuild`,
   equivalently `newgrp`/`sg`) makes the effective gid 103 while `pw_gid` stays
   1000. `newuidmap` refuses that, so unshare mode cannot start at all. The
   `sbuild` group is only needed by the old schroot mode.

Also worth knowing: `sbuild-createchroot` did not write an `aliases=` line, so
`-d resolute` did not resolve to `resolute-amd64-sbuild`. Adding
`aliases=resolute,resolute-amd64,UNRELEASED` fixes the schroot path if it is
ever needed again. The schroot is left in place as a fallback; if it turns out
to be dead weight, delete `/srv/chroot/resolute-amd64-sbuild` and its
`/etc/schroot/chroot.d` entry.

**Note.** `sg` does not exist in Ubuntu 26.04.

---

## 2026-09-22 - vcstool installed via pipx with setuptools pinned below 81

**Decision.** `pipx install vcstool && pipx inject vcstool 'setuptools<81'`.

**Why.** `python3-vcstool` is not in the resolute archive. vcstool 0.3.0 still
imports `pkg_resources`, which setuptools removed in version 81; on Python 3.14
a plain `pipx install` yields `ModuleNotFoundError: No module named
'pkg_resources'`. Injecting current setuptools (84) does not help - the pin is
the fix.

---

## 2026-09-22 - root filesystem grown inside the guest, not in VirtualBox

**Decision.** `lvextend -l +100%FREE` plus `resize2fs`, online, no reboot.
97 GB -> 195 GB.

**Why.** The volume group was already 198 GB with only 99 GB allocated to the
logical volume. Resizing the virtual disk in VirtualBox would have required
shutting the VM down for no reason.

---

## 2026-09-22 - compiz, bamf and the indicators come from the Ubuntu archive

**Decision.** `manifest.repos` lists only what actually exists upstream. Compiz,
BAMF, `unity-gtk-module`, the `indicator-*` family and `vala-appmenu-panel` are
imported with `git-ubuntu` from the Ubuntu archive instead.

**Why.** The `gitlab.com/ubuntu-unity` group was inventoried on 2026-09-22 and
holds 28 projects in three subgroups (`unity`, `lomiri`, `website`). None of
those components is among them, despite the handoff assuming they would be.

---

## 2026-09-22 - deb-src had to be enabled by hand

**Decision.** `Types: deb` changed to `Types: deb deb-src` in
`/etc/apt/sources.list.d/ubuntu.sources` on builder.

**Why.** The Ubuntu Server 26.04 installer ships deb822 sources with binary
packages only. Without source entries `sbuild` cannot fetch a package to build
and fails with no useful output - it writes to its own `*.build` log, so a
shell redirect of stdout comes back empty and hides the cause.

**Result.** `sbuild -d resolute hello` -> `Status: successful`, build time 42 s.
The pipeline is verified end to end.

---

## 2026-09-22 - screenshots go through gnome-screenshot, not xwd or scrot

**Decision.** Capture the target desktop with
`ssh target 'DISPLAY=:0 gnome-screenshot -f /tmp/shot.png'`.

**Why.** `xwd -root` and `import -window root` read the X11 root window. Under
a compositor the root window holds no wallpaper - Compiz draws the background
into its own OpenGL buffer and it never lands there. Panel, launcher and
indicators are separate windows, so they *do* appear in such a capture.

The result is a screenshot that looks exactly like a real Unity bug: a working
shell on a black desktop. We nearly filed it as one. May looked at the physical
screen from the VirtualBox window and the wallpaper was plainly there - the
standard purple Resolute Raccoon background.

`gnome-screenshot` gets it right even though it reports
`Unable to use GNOME Shell's builtin screenshot interface, resorting to
fallback X11` - the fallback still composites correctly.

**Consequences.**

- `UNITY-DISTRO-HANDOFF.md` §4 recommended `scrot` and `import -window root`.
  That advice is wrong for this desktop and has been corrected in place, with a
  note pointing here, so the next session does not repeat it.
- The handoff also asked for `scrot`/`imagemagick` to be installed on target.
  Not needed - `gnome-screenshot` ships with the desktop.
- `xwd` remains usable for individual windows, just not for the background.
- **General rule:** before reporting a bug seen in a screenshot, ask May whether
  the physical screen shows the same thing. He is sitting at the machine; it is
  the cheapest possible check, and our eyes on target are indirect.

**Rejected.** Turning off 3D acceleration on target would push the background
back into the root window and make `xwd` work - at the cost of disabling the
compositor Unity 7 is built on. That would cure the symptom by removing the
subject of study. The VM settings are correct as they are: `vram=128`,
`accelerate3d=on`, `vmsvga`.

---

## 2026-09-22 - unity 7.7.1 cannot be rebuilt in resolute: nux still needs PCRE1

**Finding.** `sbuild -d resolute` on `unity` 7.7.1+26.04.20260306-0ubuntu3 fails
at configure:

```
Package 'libpcre', required by 'nux-4.0', not found
CMake Error: The following required packages were not found:
 - nux-4.0>=4.0.5
```

**Root cause.** `libpcre3-dev`, which ships `libpcre.pc`, has been **removed
from resolute**; only PCRE2 (`libpcre2-dev` 10.46) remains. But
`nux-4.0.pc` 4.0.8 in the archive still declares

```
Requires: glib-2.0 nux-core-4.0 nux-graphics-4.0 gl glu glewmx xext x11 sigc++-2.0 libpcre
```

pkg-config resolves `Requires` transitively, so `nux-4.0` itself becomes
unresolvable. **Every package that build-depends on `libnux-4.0-dev` is
blocked, unity included.** The binaries in the archive were built while PCRE1
was still there; the source is no longer buildable today.

This is not an environment problem on our side - it reproduces in a clean
`resolute` chroot.

**Scope of the fix.** Small and well contained. PCRE appears in exactly two
files in the nux tree:

- `Nux/nux.pc.in:11` - the `Requires` line
- `Nux/Validator.h` - `#include <pcre.h>`, member `pcre *_regexp`
- `Nux/Validator.cpp` - `pcre_compile`, `pcre_exec`, `pcre_extra`,
  `PCRE_MULTILINE`, `PCRE_EXTRA_MATCH_LIMIT_RECURSION`

Four API calls in total. The PCRE2 equivalents are `pcre2_compile`,
`pcre2_match` with a `pcre2_match_data`, and `pcre2_set_depth_limit` on a match
context in place of `pcre_extra.match_limit_recursion`.

**Plan.** Port `Validator` to PCRE2, change `nux.pc.in` to require
`libpcre2-8`, and swap `libpcre3-dev` for `libpcre2-dev` in `debian/control`.
Carry it as a quilt patch with a `+unity1` version, and send it upstream - this
blocks the whole distribution, so it belongs upstream rather than in our tree.

**Rejected.** Dropping PCRE and using `std::regex` everywhere. The Windows
branch of `Validator` already does exactly that, so the code is there. But
`std::regex` does not have PCRE's syntax or semantics, and swapping the engine
under a validator silently changes which inputs are accepted. Not a change to
make while also unblocking a build.

**Noticed in passing, not our bug to fix now.** `Validator::Validate` on the
Windows branch returns `Acceptable` from both sides of its `if` - the match
result is discarded. Worth reporting upstream separately.

**Also noted.** The nux git tree is at `4.0.8+18.10.20180623-0ubuntu15`
targeting a `stonking` distribution, which is ahead of what the archive has.
Check which base the patch should sit on before sending it.
