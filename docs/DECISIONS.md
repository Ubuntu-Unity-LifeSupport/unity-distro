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

---

## 2026-09-22 - correction: the PCRE2 port already exists and was never uploaded

The previous entry said the fix had to be written. That was wrong, and the
correction matters more than the original diagnosis.

**What actually happened.** The patch exists in the nux packaging git as
`debian/patches/migrate-to-libpcre2.patch`, by Tomasz Jeruzalski and c4pp4. Its
history:

| Revision | Date | Change |
|---|---|---|
| `13366a9` -> `-0ubuntu12` | 2026-01-28 | patch added, 130 lines. Ports `Validator.{h,cpp}` to PCRE2 but **touches neither `nux.pc.in` nor `configure.ac`** |
| `3c56e89` -> `-0ubuntu13` | 2026-04-01 | patch extended, +45/-20: adds the `nux.pc.in` and `configure.ac` hunks. Changelog: "Update patch for fixing FTBFS unity (LP: #2147013)" |

So `-0ubuntu12` fixed the code but left the pkg-config metadata advertising
PCRE1. That is precisely the half-fix that breaks every reverse build
dependency while looking done from the inside.

**`-0ubuntu13` targets resolute and was never published.** The archive still
carries `-0ubuntu12`. The two revisions after it, `-0ubuntu14` and
`-0ubuntu15`, target `stonking`. The resolute upload was simply skipped.

**Verified locally, end to end.**

- Built `-0ubuntu13` from `3c56e89` in a clean resolute chroot:
  `Status: successful`, 478 s.
- `nux-4.0.pc` in the resulting `libnux-4.0-dev` now reads
  `Requires: ... libpcre2-8` instead of `... libpcre`.
- Rebuilt `unity` 7.7.1+26.04.20260306-0ubuntu3 against it with
  `sbuild --extra-package`: **`Status: successful`, 372 s**, seven binary
  packages.

**The contribution is therefore not a patch but an upload.** LP: #2147013
already exists, the fix is already written and reviewed by its authors, and we
can now show the full chain: `-0ubuntu12` breaks unity, `-0ubuntu13` fixes it,
unity builds. That is a much stronger case than a bug report describing a
symptom.

**How healthy is the unity code?** (the question §7.4 asks)

746 compiler warnings, dominated by 507 `-Wtemplate-id-cdtor` - injected-class-name
constructor spellings that C++20 deprecated - plus 68 `-Wdeprecated-declarations`
and 5 `-Wmaybe-uninitialized`. Noisy and dated, but it compiles clean in six
minutes on four cores. Less fragile than the handoff implied.

---

## 2026-09-22 - sbuild builds go to /var/tmp, not $TMPDIR, and not under $HOME

**Decision.** `~/.config/sbuild/config.pl` sets
`$unshare_tmpdir_template = '/var/tmp/sbuild-claude/sbuild-unshare-XXXXXX'`.

**Why, in two steps.** Unity's build needs about 4 GB.

1. sbuild in unshare mode unpacks the chroot into `$TMPDIR`. Here `/tmp` is a
   **3.7 GB tmpfs in RAM**, so the whole build ran in memory and died with
   `fatal error: cannot write PCH file: No space left on device` - while the
   disk had 177 GB free. Precompiled headers on `-j4` overflow it quickly.
2. Moving the template to `/home/claude/build-tmp` then failed with
   `Error creating chroot session`. sbuild bind-mounts the home directory into
   the chroot, so a chroot root nested inside `$HOME` cannot work. It has to
   live outside.

**Also.** `sbuild` runs `debian/rules clean` on the host before packing the
source, which needs the build dependencies installed locally - exactly what the
chroot is supposed to avoid. Use `--no-clean-source` on a git tree.
