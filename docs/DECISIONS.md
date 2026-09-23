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

---

## 2026-09-22 - nux -0ubuntu13 verified on target: no regression

Installed `libnux-4.0-0` and `libnux-4.0-common` `-0ubuntu13` on target over the
archive's `-0ubuntu12`, rebooted, and ran the TESTING.md checklist. This is the
verification an SRU needs.

**Proof the new library is actually in use.** `/proc/$(pgrep -x compiz)/maps`
contains `libnux-4.0.so.0.8.0` together with `libpcre2-8.so.0.14.0` and **no
PCRE1 mapping at all**.

| Check | Result |
|---|---|
| Fresh boot to greeter | works |
| Login, Unity session starts | works |
| Panel, launcher, wallpaper | render correctly |
| Dash (Super) | opens, search and lenses present |
| HUD (Alt) | opens |
| Session indicator, shutdown menu | opens, all entries present |
| Sound indicator | opens, sliders and media controls work |
| Window decorations on a GTK4 + libadwaita header bar app (file-roller; originally mislabelled GTK3, corrected 2026-09-23) | correct, Unity-style |
| Crashes during the run | none |

**On the crashes we did see.** Three, none attributable to this change.

- `compiz`, SIGSEGV, during `unity --replace`. The crashing process was the
  **old** compiz (pid 3437), which had the previous libnux mapped; replacing a
  shared object on disk does not alter an already-mapped process. An artefact
  of restarting the shell in place, not of the package. A full reboot afterwards
  produced no crash at all.
- `light-locker`, SIGABRT. Seen **before** we touched anything (20:23) and again
  later (22:33). Pre-existing and reproducible. This is the component that
  replaced gnome-screensaver in 26.04 - worth its own investigation.
- `unity-control-center`, SIGSEGV, with a follow-up crash inside `ld.so` when
  the session relaunched it under the `libgtk-nocsd.so.0` preload.
  `unity-control-center` **does not link libnux at all** (checked with `ldd`),
  so this change cannot be the cause. Not reproducible by launching it from a
  shell - it survived 20 s runs both with and without the preload - so it needs
  interaction to trigger. Logged as a separate lead, not chased.

Crash files kept in `~/evidence/` on builder.

**Conclusion.** `-0ubuntu13` fixes the FTBFS and introduces no visible
regression on a live 26.04 desktop. This is the evidence for the SRU.

---

## 2026-09-22 - the global menu is already empty for headerbar applications

Not a regression, and not something we introduced - a measurement of where
Layer B has to start.

Opened `file-roller`, a GTK4 + libadwaita application (originally written here as GTK3 - wrong, corrected 2026-09-23; the measurement stands, the classification did not) with an `AdwHeaderBar`
and a hamburger button. The panel shows only the application name; there is no
File/Edit/View to be seen. Querying the registrar directly:

```
$ gdbus call --session --dest com.canonical.AppMenu.Registrar \
    --object-path /com/canonical/AppMenu/Registrar \
    --method com.canonical.AppMenu.Registrar.GetMenus
([(uint32 48234500, '', objectpath '/')],)
```

The window **is** registered, with an empty service name and an object path of
`/`. So the plumbing is connected and there is simply no menu model on the
other end - exactly the gap Layer B's GTK4/libadwaita patch has to close, and a
concrete before-picture to measure any patch against.

Window decorations on the same application are correct and Unity-styled, which
matches what the 26.04 release notes claim was fixed.

Screenshot: `docs/screenshots/2026-09-22-headerbar-app-no-global-menu.png`.

---

## 2026-09-23 - the LD_PRELOAD precedent was installed on our own machine

**Searched for:** whether anyone had already built an `LD_PRELOAD` shim for
GTK4, and where the source of the one we knew about - `libgtk-nocsd.so.0` -
lives.

**Where:** the installed system on builder and target (`apt-cache policy`,
`apt-cache showsrc`, `apt-cache show`, `dpkg -l`), and the web through the host
session.

**Found, and it was closer than expected.**

`gtk3-nocsd` and `gtk-nocsd` are two different source packages. The current one
is `gtk-nocsd` 0~20260321+0b77e1b-1, packaged by the Debian UBports team, from
`salsa.debian.org/ubports-team/gtk-nocsd`. Its `libgtk-nocsd0` binary describes
itself as

> a small LD_PRELOADable library used to disable the client side decorations
> (CSD) of GTK3, GTK4, and libadwaita

and carries `Task: ubuntu-unity-desktop`. It is installed on target. We had
already seen it - in the `unity-control-center` crash, where it appeared in the
command line of the follow-up `ld.so` crash and was written off as an
unrelated detail.

**What this changes.**

1. An `LD_PRELOAD` shim for GTK4 is not an exotic proposal in Ubuntu Unity. It
   is a packaged, shipped, task-installed mechanism in the flavour itself. When
   the time comes to talk to the team, we are proposing a second use of
   something they already run rather than a new idea.
2. `gtk-nocsd`'s `debian/` is a worked example of how to package such a
   library: where it goes, how it is turned on in a session, how it enters the
   task. Read it before writing our own packaging.
3. Their code interposes not only `gtk_window_present` and
   `gtk_widget_set_visible` but also `gtk_window_get_titlebar`,
   `gtk_window_get_child` and `gtk_widget_get_first_child` - the very calls our
   menu search walks. Our shim does not see the real widget tree; it sees the
   tree nocsd presents.

**Coexistence tested** with `dialogtest.c`, all four combinations:

| Loaded | menubar attached | GTK warnings |
|---|---|---|
| shim only | yes | 0 |
| nocsd only | no (expected) | 1 |
| nocsd, then shim | yes | 1 |
| shim, then nocsd | yes | 1 |

Our shim works in either load order. The single warning is nocsd's own - it
appears with nocsd alone and is identical with the shim present:
`gtk_widget_size_allocate(): attempt to allocate GtkWindowHandle ... with width
420 and height -1`. We add none.

**Not chased:** whether `unity-control-center`'s crash is nocsd's doing. Worth
revisiting with the LD_PRELOAD removed first, which is the general rule for
investigating any bug on this system.

---

## 2026-09-23 - rule 0: find out whether it is already solved

**Decision.** Before writing a line of code for a problem, establish whether it
is already solved. Recorded in `docs/CONTRIBUTING-UPSTREAM.md` section 0,
summarised in `CLAUDE.md`, and in the `upstream-contribution` skill. Two lines
added to the pre-submission checklist.

**Why.** Three cases in one day, each further along than the last:

1. The nux PCRE2 port existed for six months; we had localised the problem to
   the file and line and were about to rewrite it.
2. `vala-panel-appmenu` was recorded as an open question because we searched a
   transposed name.
3. The `LD_PRELOAD` approach for GTK4 was built as new. The mechanism was
   already installed on the machine, shipped with our own flavour, and visible
   in a crash dump we had dismissed.

The rule is bounded so it does not become paralysis: about twenty minutes on
the system, the package history and the trackers, then write down where you
looked and carry on. **The record goes in either way.** "I do not remember
whether I checked" means "I did not check".

---

## 2026-09-23 - the handoff checked against the real system, section by section

**Searched for:** whether each factual claim in `UNITY-DISTRO-HANDOFF.md`
holds on resolute today, after the plan had already misled us several times.

**Where:** the host session went through all nine sections against the archive
(`apt-cache policy`, `apt-cache showsrc`), the web, and the sources on builder,
and wrote its findings to `~/HANDOFF-CORRECTIONS.md`. Every package claim in
that file was then re-checked independently here with `apt-cache` before being
written into the handoff - copying unverified package facts into a correction
about unverified package facts would repeat the very mistake. All matched.

**Found.** Fifteen corrections, now made in place in the handoff with a note
under each, plus Appendix B summarising them. The ones that change the work:

- **Qt has no global menu in 26.04 at all.** `appmenu-qt5` does not exist in
  the archive; it was dropped around 16.10 (LP #1612767) and never worked with
  Qt6. Layer B is therefore larger than it looked: GTK4 needs our shim, GTK3
  has an existing module, and Qt has to be built from nothing, probably as a
  Qt platform theme exporting through dbusmenu the way KDE does.
- **The file manager moved to GTK4.** The manual checklist told us to test the
  GTK3 path on it. `gedit`, `synaptic`, `gnome-terminal`, `pluma` and `caja`
  are still GTK3; `nautilus`, `file-roller`, `gnome-text-editor` and
  `gnome-calculator` are GTK4 + libadwaita. TESTING.md now has a GTK4 branch,
  which it lacked entirely.
- **Six known bugs, not five**, and the workarounds point at mechanisms better
  than the symptoms do.

**The pattern.** The handoff was written without access to the system.
Everything checkable by reading publications was accurate; everything that
needed `apt-cache policy` drifted. No strategic decision failed the check.
Rule: verify "package X exists and does Y" in the archive before building a
plan on it.

**Two corrections to our own records**, found in the same review:

- `file-roller` was described as a GTK3 application in two places in this file
  and one in TESTING.md. It is GTK4 + libadwaita. The measurements were right
  and are unchanged; the classification was wrong and is corrected in place.
- The record on screenshots says installing `scrot` on target is not needed.
  That is accurate, but a chat message said "scrot там нет", meaning not
  installed on target, which reads as "not in the archive". It is in the
  archive, `1.12.1-1build1`; it is unused because under Compiz it captures a
  black background, not because it is missing.

**One correction to the correction.** The review listed "screenshot of the
login screen as the lightdm user with its XAUTHORITY" as not yet tested. It was
tested on 2026-09-22 while capturing the greeter: as the lightdm user it fails
with `Authorization required`, because `/run/lightdm/root/:0` is root-owned
0600; it works as root. The handoff now says so.
