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

- _(Wrong - corrected 2026-09-24 below: Qt 5.7+ exports its own menubar and it works.)_
  **Qt has no global menu in 26.04 at all.** `appmenu-qt5` does not exist in
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

---

## 2026-09-23 - light-locker: diagnosis, rule 0, and why the fix is not PR #153

**Searched for, before writing code** (rule 0): a newer light-locker in any
series, an existing bug, an upstream fix, and neighbouring projects' handling.

**Where:** the system and package history here (`rmadison`, changelog), and
the web through the host session.

**Found.**

- light-locker is `1.8.0-3ubuntu4` in both resolute and stonking. Nothing newer
  anywhere; the code is Debian's 1.8.0 from 2019 plus one Recommends line.
- **LP: #2038808 already exists** - an automatic crash report for
  `init_session_id`, no analysis. LP: #2167241 may be related.
- **Upstream is dead** since 2020. So the route is the Ubuntu package, not an
  upstream merge request - a change from what §3 of the handoff assumed.
- **Upstream PR #153** (2020, unmerged) aims at the same problem. Read before
  writing ours, and it turned out not to fix this case:
  - it never handles `XDG_SESSION_PATH`, so on 26.04 it would still abort one
    step later - which is exactly what our first patch alone did;
  - it merges `session_id` (a D-Bus object path) and `sd_session_id` (a logind
    session ID) and passes the path to `sd_session_is_active()`. Measured from
    a user service: that returns `-EINVAL`, so the "refuse to lock an inactive
    session" check silently stops working. A likely explanation for the
    locking problems reported on the PR.
- 1.9.0 is no fix either: upstream issue #141 reports it regressing the same
  error, and its new `XDG_SESSION_ID` fallback does not apply here because the
  variable is absent.

**Mechanism, proved with the system's own tools** rather than inferred:
`GetSessionByPID` fails for a process in a user service and works for the
session leader; `loginctl show-user -p Display` names the graphical session and
`GetSession` on it returns the same path. The process tree shows
`unity-session.service` running `cinnamon-session --session=unity`, which
launches light-locker.

**Two aborts, found one at a time.** With the first patch alone light-locker
got past the session lookup and died in `query_seat_path()` on the missing
`XDG_SESSION_PATH`. The first abort had been hiding the second. Reporting
"fixed" after the first patch would have been wrong.

**Tested for locking, not just survival**, because that is where PR #153
failed: `light-locker-command -l` made the user session inactive and brought
up the greeter on `:1` in unlock mode. Unlock itself is untested - no password.

**Process notes worth keeping.**

- The first rollback request was reported done but had not happened: the VM
  had been up nine hours and the marker was still there. `CurrentSnapshotName`
  shows the snapshot the current state descends from, which was already the
  target snapshot, so it proves nothing. The marker check caught it, which is
  what it is for.
- The crash file on the clean system was dated before the login - it lived in
  the snapshot, and apport does not write a new one while an unreported one
  exists. The journal is the evidence for a given boot, not `/var/crash`.
- `sbuild` on a git tree needs `--no-clean-source`. Recorded on day one and
  forgotten on day two.
- `gbp pq export` re-exports every patch and rewrites index hashes and hunk
  offsets in ones we did not touch. Restore them before committing, or a
  two-file contribution arrives as a five-file one.
- Version bumped to `+unity2` rather than rebuilding `+unity1`, which had
  already been published and installed.

---

## 2026-09-23 - the power button works; it asks first

The host session reported `controlvm acpipowerbutton` as "not working":
`VMState` stayed `running` for over a day after it. The observation is right
and the conclusion was not.

Measured on target:

- `systemd-inhibit --list`: `unity-settings-daemon` holds a **block** inhibitor
  on `handle-power-key`, so logind hands the key to it.
- its power-button action is `interactive`.
- sending the key into the session (`xdotool key XF86PowerOff`) brings up a
  dialog, "Выключить систему сейчас?", owned by `cinnamon-session-quit` in
  `unity-session.service`. Escape closes it and nothing shuts down.

So the button opened a dialog and waited for a person. Designed behaviour.
TESTING.md now says to power target off with `systemctl poweroff` over ssh.

The measurement turned up something more useful than the correction. There are
**two different shutdown dialogs**: Unity's own, from the session indicator,
and `cinnamon-session-quit`'s, from the power key. And the two settings daemons
running side by side disagree about the power button - `unity-settings-daemon`
says `interactive`, `cinnamon-settings-daemon` says `suspend`. Neither is yet
shown to cause known issue #6, the double dialog, but they are where to look.

Also recorded here: unlocking was verified by hand by May, corroborated by
LightDM's log on that boot (`Authenticate result for user mike: Success`,
`Unlocking login1 session 1`), and every light-locker evidence file now names
the boot it came from. One of them, `02`, was re-collected: its first version
came from a boot that also had our GTK4 shim installed and did not say so.

## 2026-09-23 - #6 in cinnamon-session would be a feature, not a regression fix

Before any code for #6, May asked whether cinnamon-session once had an
`org.gnome.Shell` path and lost it. It did not, in any release: the copy
inherited from gnome-session was renamed to `org.cinnamon.Shell` on the day of
the fork (`53d2cda`, 2013-06-02) and deleted two days later (`38d042a`,
"Remove gnome-shell stuff we don't use"). The first tag, 1.9.2, already has
neither. Details and the commit table are in
`docs/research/shutdown-path/README.md`.

Consequence for wording: a cinnamon-session change that falls back to
`org.gnome.Shell` is a proposal for a new capability - using the end-session
dialog of any shell that speaks gnome-session's protocol - and must be
written up that way. The word "regression" does not appear in anything about
#6.

The dialog code is identical between 6.4.2 and upstream HEAD, so such a patch
would not need rebasing.

### Searched, not found (rule 0, done by the host session)

Recorded as searched and empty, so nobody repeats the search and nobody
claims more than was found:

- **Two settings daemons fighting over the power key** (`unity-settings-daemon`
  and `cinnamon-settings-daemon` in one session, `interactive` against
  `suspend`): nothing in Launchpad for either package, in Cinnamon's trackers,
  or on the Mint forums. Only unrelated autostart problems and "how to turn
  off the power-button dialog in Cinnamon". If this turns out to matter, it is
  unreported.
- **#2, the dead menu after cancelling**: not filed anywhere. The nearest is
  LP #1521116 ("session dialog doesn't close on first esc use"), a different
  mechanism in `shutdown/SessionView.cpp`, Fix Released in Unity 7.4/7.5, 2016.
- **#6, two dialogs**: one Linux Mint forum thread, "2 shutdown dialogs on
  power button press" (Mint 22.1), closed unanswered. Same fallback line, but
  the cause is a timeout of a running Cinnamon shell; ours is an absent shell.
  Related, not the same bug.
- **cinnamon-session used under another shell**: no public discussion found.

## 2026-09-23 - Unity's unit tests do not build or run on 26.04 as shipped

The package builds with `-DENABLE_UNIT_TESTS=OFF`, so nobody notices. To test
the fix for #2 we built `test-gnome-session-manager` in a disposable chroot
(mmdebstrap, our nux 0ubuntu13 from aptly) and hit three separate breakages,
each worked around in the harness only, none in the patch:

1. **C++ standard.** `CMakeLists.txt` forces `-std=c++14`; googletest 1.17 in
   26.04 requires C++17 and the bundled gtest source does not compile.
   Harness: `-std=c++17`.
2. **GCC 15.** `tests/gmockvolume.c` passes an incompatible function pointer
   to a GObject macro; GCC 15 makes `incompatible-pointer-types` an error.
   Harness: `-Wno-error=incompatible-pointer-types` for C.
3. **No VidMode under Xvfb.** The test main creates a Nux window, and
   `nux::GraphicsDisplay::CreateOpenGLWindow` dereferences
   `m_X11VideoModes[0]` (`NuxGraphics/GraphicsDisplayX11.cpp:297`) without
   checking that `XF86VidModeGetAllModeLines` succeeded. Xvfb has no
   XFree86-VidModeExtension, so the binary segfaults before the first test.
   Harness: Xorg with the dummy driver - which Unity's Build-Depends already
   list (`xserver-xorg-video-dummy`), so upstream once ran them that way.

With those, `TestGnomeSessionManager` runs 47 tests. Each of the three is a
small upstream contribution in its own right (nux for 3, Unity for 1 and 2);
recorded here, not queued yet. Harness scripts: see
`docs/upstream/unity-stale-pending-action/README.md`.

## 2026-09-23 - #2 fixed in Unity; the first fix was incomplete, and why

**Where the change lives.** `unity` is a `3.0 (native)` package, so there is no
quilt series to add to: `debian/patches/` would be ignored. Our changes are
commits on `unity/resolute` in `packages/unity` (pushed to
https://github.com/Ubuntu-Unity-LifeSupport/unity), each followed by a
changelog commit for the `+unityN` build. The upstream copy is a separate
branch, `mr/stale-pending-action`, cut from upstream's `ubuntu/devel` with one
squashed commit - what a merge request needs, without our changelog.

**The first fix was wrong in a way the unit test could not show.** `+unity1`
dropped a pending action when a request for a *different* action arrived,
which fixed #2. It kept taking a request for the *same* action as the session
manager's confirmation. Testing that leftover case on target restarted the
machine: pending `REBOOT` (chosen in Unity's dialog, then cinnamon-session's
dialog cancelled) plus the indicator's "Выключение...", which asks for the
restart dialog on purpose, makes Unity emit `ConfirmedReboot`, and
indicator-session calls logind's `Reboot` 6 ms later. Reproduced on the
archive package too - it is an old bug, not ours, but `+unity1` did not fix
it. We had described it as "one lost click" from reading Unity alone; the
consequence lives in indicator-session.

`+unity2` accepts the confirmation only from the owner of
`org.gnome.SessionManager`. A second unit test sends `Open` from a separate
bus connection, the way the indicator does; the fixture otherwise serves the
session manager and the shell from one connection, which is why the first
test could not catch it.

Lesson, generalised: a limitation written into a commit message ("costs one
click") was a claim, and it had not been measured. It was measured the same
hour, and it was wrong.

`+unity1` stays in the history and in aptly as built; `+unity2` supersedes it.

### Searched, not found: the restart without a dialog (rule 0)

Launchpad API (unity, indicator-session, cinnamon-session) by us; forums, Ask
Ubuntu, Reddit and the general web by the host session. Nothing describes it.
Closest: LP #1414950 (14.10, 2015, "shuts down immediately" from the menu),
closed by its reporter after a reinstall with no diagnosis. The Ubuntu Unity
forum could not be searched - `www.foss.ubuntuunity.org` fails the TLS
handshake from builder and from the host alike.

Also added to the checklist, on the host session's suggestion: every
consequence or limitation stated in outgoing text is measured, or marked as an
assumption.

## 2026-09-24 - #6: option A over option B, by measurement

Both options for the double dialog were built and run on target; the table and
the logs are in `research/shutdown-path/` ("#6: options A and B, measured").
Option B (Unity calls `RequestShutdown`/`RequestReboot`) removes the second
dialog in two lines, but with an inhibitor it leaves cinnamon-session stuck in
the query phase with nothing on screen, and the next attempt restarts through
logind past the inhibitor. Option A (cinnamon-session asks `org.gnome.Shell`
after the query phase, as gnome-session does) gives one dialog on every path
and Unity's dialog on the power key; its remaining gap - Unity confirming its
own pending action despite inhibitors - is Unity's, and exists under
gnome-session too. Next: that Unity fix, then A and it measured together.
Nothing proposed yet; the direction is May's call.

**Correction.** We wrote that cinnamon-session under Unity gets
`NAME_HAS_NO_OWNER` from `org.Cinnamon`, logged at `g_debug`. It gets
`ServiceUnknown` and logs a CRITICAL - found when the first build of option A,
which tested for `NAME_HAS_NO_OWNER`, did nothing. Research corrected in place,
host session told.

**Incident, no damage.** A `dch` failure did not stop the `sbuild` after it
(the commands were joined by a newline, not `&&`), so sbuild started on the
experiment's code under version `+unity2` and overwrote the local
`unity_..+unity2.dsc`/`.tar.xz` before it was killed. The `+unity2` binaries
and aptly were untouched (aptly holds only `.deb`s). The source package was
regenerated from `dd954ff0`; `dpkg-source -b` is reproducible here (two
builds, same SHA-256). Experiments since go to their own version
(`+unity2+optb1`, `6.4.2-1+optA2`), their own `--build-dir`, and sbuild runs
only after a version check.

## 2026-09-24 - unity-gtk4-menu: stand-ins for class actions (agent B)

**Rule 0, where we looked.** Archive and installed system on a clean
`target2`; the GTK 4.22.4 source; the web through the host session - GTK
issues and MRs, vala-panel-appmenu, KDE's plasma-integration and discuss
thread. No one exports GTK4 widget or class actions over D-Bus, and GTK has no
public getter for a class action's enabled state. Details and links in
`research/layer-b/` ("Class actions").

**Correction.** `research/layer-b/` said yelp's "About Help" comes from a group
inserted with `gtk_widget_insert_action_group()`. It is a class action
(`gtk_widget_class_install_action` on `YelpWindow`). Corrected by a new section
that quotes the source; the original text is kept with a pointer to it.

**Decision.** Proxy only what can be identified positively: stateless class
actions found on the menu's owner widget or its ancestors. Each gets a
stand-in in the window's action map, activated with
`gtk_widget_activate_action_variant()` from the owner. Rejected alternatives:
- adding the original name to the window's map - shadows nothing today because
  the muxer checks class actions first, but it puts our action under the
  application's own name, where the application might add or look one up;
- interposing `gtk_widget_insert_action_group()` to catch inserted groups -
  another exported GTK symbol in a library preloaded into every process, for a
  case not yet seen on a real application;
- proxying every unresolved name blindly - an enabled item for an action that
  may not exist, and wrong state for property actions.
The stand-in is always enabled; see the research for why that is acceptable.

**Found on the way, not ours:** the archive has `qtlomiri-appmenutheme-qt5`
("Qt platform theme for exported application menus to Lomiri"). STATUS says Qt
has no global menu in 26.04 because `appmenu-qt5` is gone; this may be the
piece to start from. Not tested.

## 2026-09-24 - unity-gtk4-menu: which menu to export (agent B)

Rank every menu button by shown, then `primary`, then the number of
`app.`/`win.` items, then tree order. `primary` first was tried and measured:
it took the hidden tab overview's menu in gnome-console, because libadwaita
marks that one primary and the application does not mark its real main menu.
Visibility has to include child-visible on the ancestors, since nothing is
mapped at realize. Considered and not taken: choosing by score alone - fails
gnome-logs, whose boot list has more `app.`/`win.` items than its main menu;
choosing by position in the header bar - applications put the main menu at
either end, and yelp's header bar is not even the titlebar. Evidence in
`research/layer-b/` ("Choosing the main menu").

## 2026-09-24 - unity-gtk4-menu: reaching gjs and Python through g_module_symbol (agent B)

**Rule 0.** The installed system had the answer: gtk-nocsd, preloaded in
Ubuntu Unity, intercepts `g_module_symbol()` to reach introspection-based
applications. We use the same function as a trigger only. `dlopen`
interposition (changes the caller for `RUNPATH` resolution in every process),
`LD_AUDIT` and an idle callback (too late) were rejected; details in
`research/layer-b/` ("gjs and Python applications").

**Order is load-bearing.** Hook after the real lookup returns, never before:
gtk-nocsd fetches its types only in its own `g_module_symbol`, and a class
initialisation of ours in between makes it miss them and abort libadwaita
applications. The comment at `g_module_symbol()` in the source says so.

**Found, not ours, not reported:** gtk-nocsd crashes gnome-sound-recorder on
its own (SIGSEGV, reproduced with only gtk-nocsd preloaded), and its
`GTKNoCSDGetReferences` never fetches types if it first sees GTK in a
`GetTypes=false` call - latent until another library initialises a GTK class
first. Upstream is https://codeberg.org/MorsMortium/GTK-NoCSD. Whether to
report is May's call.

## 2026-09-24 - unity-gtk4-menu: enabled state by intercepting the setter (agent B)

GTK has no getter for a class action's enabled state; the setter is public.
0.7 interposes `gtk_widget_action_set_enabled()` (PLT for C/Rust, handed out
from `g_module_symbol()` for gjs/Python), calls the real one first, and
records the state on the widget. Considered: reading GTK's private muxer
(`widget_actions_disabled` bitmask) - layout changes between GTK releases
would turn a wrong offset into memory corruption in every GTK4 process;
dropping `hidden-when` items from the export - loses items that become valid
later (Leave Fullscreen). Evidence in `research/layer-b/` ("Stand-ins follow
the enabled state").

## 2026-09-24 - #6 shipped to our archive as three packages at once

May approved publishing unity `+unity4`, cinnamon-session `6.4.2-1+unity1`
and compiz `+unity1` to aptly. They are one change: option A (cinnamon-session)
gives one dialog but exposes a compiz exit race (`exit(0)` from the XSMP die
callback while GDBus writes), and unity's two fixes make inhibitors visible on
the menu path. Published together, verified together from a clean snapshot
via apt. `+unity3` of unity was built, installed on target and found
incomplete; it was never published, and its version is not reused.

The host session noted that it had not heard May's approval itself - right:
an agent's report of May's approval is not approval. It came in this agent's
own chat ("Давай, публикуй трио в aptly"), and publishing to our own aptly is
internal in any case.

## 2026-09-24 - unity-gtk4-menu: no late-menu mechanism (agent B)

The "menus built after realize" item was a misdiagnosis: gnome-font-viewer has
no menu, and gnome-contacts shows a setup window before its main window, whose
menu 0.7 already exports (verified on the first-run path). A placeholder-menubar
mechanism was written and deliberately not shipped - it would export empty
menubars for menu-less applications with no application known to need it. The
diff is kept in `research/layer-b/late-menu-placeholder.diff`. Lesson recorded
for this package: read the application's UI definition before concluding why
a menu is missing.

## 2026-09-24 - cinnamon-settings-daemon does not run under Unity; `pgrep -f` counted itself

The 2026-09-23 finding "two settings daemons run side by side and disagree on
the power button" was wrong. `cinnamon-settings-daemon` is installed
(`unity-session` depends on it), but every `csd-*` autostart entry carries
`OnlyShowIn=X-Cinnamon;`, the session's desktop is `Unity:Unity7:ubuntu`, and
`unity.session` lists only `unity-settings-daemon` as required. On a clean
snapshot no `csd-*` process exists. The `suspend` value is an unread gsettings
key.

The false positive came from `pgrep -cf cinnamon-settings-daemon` run inside
`ssh target '...'` - the `bash -c` running it has the pattern in its own
command line. Same trap as `pkill -f apport-gtk` killing its own shell today.
Rule: with `pgrep -f`/`pkill -f`, write the pattern so it cannot match itself
(`[c]innamon-settings-daemon`), or match the process name with `-x`.
ARCHITECTURE corrected in place. Item closed; nothing to fix.

## 2026-09-24 - Correction: Qt has a global menu in 26.04 (agent B)

The handoff-review entry above ("Qt has no global menu in 26.04 at all") was
inferred from `appmenu-qt5` being absent and never measured. Qt 5.7+ exports
its menubar itself through `com.canonical.AppMenu.Registrar`, which
unity-panel-service provides. Measured on a clean `target2`: Qt5
(speedcrunch), Qt6 (featherpad) and KDE (kcalc) menus appear in the panel,
activate, and are searchable in the HUD. Layer B needs no Qt work. Details in
`research/layer-b/` ("Qt: the global menu already works"). The earlier entry
is left as written, with this correction below it.

## 2026-09-24 - agent A's Layer A list: where each item ended

May: fix locally, upstream last. Of the six items agent A took:

1. #1 cursor after login - candidate fix published (unity-settings-daemon
   `0ubuntu7+unity1`: the cursor plugin no longer hides the pointer at start).
   Not reproduced here; the release notes' description (hover still
   highlights) fits the mechanism.
2. #3 cursor stops responding - not reproduced in 400 UI actions and 60 lock
   cycles; sensor and scripts in `tools/grab-probe/`. Open.
3. Two settings daemons - not a bug; cinnamon-settings-daemon does not run
   under Unity (measurement error, corrected).
4. #2 logout path - found and fixed a hang (cinnamon-session `+unity2`) and a
   logind bypass (unity `+unity5`).
5. unity-settings-daemon crash in `libcolor` at restart - not seen in the
   eight restarts since compiz `+unity1` (plus several u-s-d restarts); it
   crashed at almost every restart before. Closed as a probable consequence of
   the compiz exit crash, not investigated further.
6. Unity unit tests - build and pass from a clean tree (`f0343140`); with
   agent B's nux `+unity1`/`0ubuntu15+unity1` also under plain Xvfb.

Also: the user's password is unknown to agents; tests unlock through
`loginctl unlock-session` (one wrong guess was made and is not repeated).

## 2026-09-24 - known issue #4: fix basicwallpaper, not the session script

The wallpaper over Calamares is the OEM first-time setup session (xfwm4 +
`basicwallpaper` + Calamares), and the cause is `basicwallpaper` mapping a
focusable fullscreen window, which xfwm4 raises whenever it has focus.
Reordering or delaying the session script would only hide the startup race;
Alt+Tab would still bring the wallpaper up. So the window itself becomes a
desktop window that takes no focus, on X11 only, since Kubuntu runs the same
binary under Wayland. calamares-settings-ubuntu `1:26.04.12+unity1`.

Rule 0, where we looked: the installed system and the ISO manifest (no other
wallpaper helper), the package changelog and the Launchpad branches up to
`ubuntu/stonking` (26.10) - basicwallpaper unchanged since the CMake bump;
Launchpad bugs of calamares-settings-ubuntu and calamares for "wallpaper",
"basicwallpaper" and "OEM" (all statuses) - nothing about this. Not solved
anywhere we could see. Details in `research/calamares-oem/`.

## 2026-09-24 - compiz restart: four fixes, all local

Checking the release notes' side bug of the #3 workaround (`killall -1
compiz` sends windows to the first workspace) found four bugs; all fixed in
our packages, nothing proposed upstream (May: upstream last).
`research/compiz-restart/` has the measurements. Published together: unity
`+unity8`, compiz `+unity2`, gtk-nocsd `+unity2`.

Rule 0, where we looked:
- Unity: `ThumbnailGenerator.cpp` and `DecoratedWindow.cpp` unchanged in
  Ubuntu's tree since 2021 (`git log`); web search for missing decorations
  after a compiz restart found only the gtk-window-decorator era (11.04).
- compiz: `setWindowFrameExtents` unchanged since the imported
  0.9.14.2+25.10.20250930; Compiz Reloaded compiz-core#187 / !179 is a
  different bug (0.8 C code, output selection on multi-monitor).
- gtk-nocsd: **found** - both crash-handler bugs are fixed upstream
  (d851645, 664d8c6, 2026-03-28, in 4.0); Debian has 4.8. We backport the
  two commits instead of packaging 4.8 for resolute: the rest of 4.x changes
  how GTK windows look, which is not what we set out to change. Worth an SRU
  request later.

Kept as is: gtk-nocsd is preloaded into compiz and the other session
services through environment.d, so its crash restart and systemd's
`Restart=` both answer a crash; systemd wins, a second compiz lives ~1.5 s.
Measured harmless; not changed.

Target's clock was 1 h 07 min behind and not synchronised; apt refused our
`InRelease` as not yet valid. Set from builder (`date -u -s @<epoch>`). After
a host sleep check both VMs' clocks before `apt update`.

## 2026-09-24 - logout with the new packages; a login race found

Six logouts with unity `+unity8`, compiz `+unity2`, gtk-nocsd `+unity2`,
cinnamon-session `+unity2`: one dialog, no crash; compiz left through the
XSMP `_exit` five times and through a clean SIGTERM teardown once
(`research/compiz-restart/`, "Logging out"). Test method worth keeping: drive
the cycle from root with `systemd-run` and stay off ssh as mike, or the user
manager survives the logout and the next login is not a real one.

Found: 2 logins in 7 had gvfs (and everything waiting on it: the desktop)
blocked for 120 s - unity-session's `run-systemd-session` stops
`graphical-session.target` at session start while ibus-daemon's D-Bus
activation of gvfs is starting; dbus-daemon waits out its timeout. Open; not
fixed.

## 2026-09-24 - login race: guard the stop in run-systemd-session

`run-systemd-session` stops graphical-session.target at every login to clear
leftovers. Stopping an inactive target still kills PartOf units being started,
and ibus-daemon's D-Bus activation of gvfs is often being started then;
dbus-daemon waits 120 s. Proved with a deterministic model (120.0 s vs 2.3 s)
and timestamps from a real login; fixed by stopping only when a target is
not inactive (unity-session `49.4+unity1`, in aptly). 0 in 6 logins after, 3
in 13 before. `research/login-gvfs-race/`.

Considered and not done: stopping the targets before Xsession starts ibus
(would move code into Xsession.d for an ordering systemd cannot express), and
making gvfs not PartOf the session (not our package, and the stop exists
precisely for such units). The guard removes the stop in the normal case and
keeps the original intent after a crashed session.

Rule 0: the script is unchanged in unity-session since 2025 and comes from
Ubuntu's old gnome-session; nothing found about this race.

## 2026-09-25 - rebuild five dead indicators ourselves instead of switching to Ayatana

indicator-datetime, -power, -session, -sound and -keyboard could not be built
in resolute, so no fix could ever reach them. They were made buildable with the
smallest possible changes (CMake minimum, GCC 15 casts, test adaptation to
libnotify 0.8, build-deps), with no behaviour change, as +unity1.

Rule 0: 26.10 (stonking) fixes only sound (0ubuntu10, cherry-picked) and
keyboard (0ubuntu3 adds `lightdm-vala`; we did the same, plus `systemd-dev`);
datetime, power and session are unchanged there; upstreams are bzr-only and
dead. Replacing them with the Ayatana indicators was not considered here: that
changes the panel's components and is May's call. `research/indicator-ftbfs/`.

## 2026-09-25 - gtk-nocsd: take 4.8 whole, not a cherry-pick (agent A)

LP #2158965 (Chromium without window buttons under Unity) is fixed upstream in
ecd66fe (4.0). We ship Debian's 4.8-1 merged into our branch as
`4.8-1+unity1` rather than ecd66fe alone: ecd66fe conflicts with our
2026-03-21 snapshot (33 earlier commits change the same file), 4.8 is what
Debian and 26.10 carry, and it also fixes the gnome-sound-recorder crash
recorded on 2026-09-24. The risk - six months of behaviour changes in a
library preloaded into every session process - was checked with 13
applications side by side with the old library, the crash handler, a compiz
SIGSEGV and a logout cycle; the only visible changes are upstream's header
titles.

Rule 0: the fix and its confirmation by the reporter are on codeberg #67;
Launchpad has no SRU in progress (the bug is Confirmed, with a request to
test in 26.10). `research/gtk-nocsd-4.8/`.

## 2026-09-25 - indicator-keyboard: fix the test, make tests fatal again

The activate-character-map abort (LP #1968333) is a Vala >= 0.55.1 codegen
bug hit by the test's mock, not a service bug. We change the mock to
`notify_property()` rather than wait for Vala, and drop `|| true` from
`debian/rules`, since the suite now passes 9/9 in sbuild. The cost: a future
test regression (or an environment change in the chroot) fails our build
instead of passing silently. That is the point of the tests.

Rule 0: Vala main and 0.56.19 unchanged, no Vala issue; 26.10 0ubuntu4 still
fails; Ayatana (C rewrite, no tests), Debian (no package), gitlab forks (same
line) have nothing. Checked `lib/`: the service only connects to notify, never
emits it that way.

## 2026-09-25 - release re-check of agent A's fixes: patch stays everywhere (agent A)

Rule 0's new last step, applied backwards to everything A carries: does a
newer release already contain the fix, and what would that version cost?
Measured by builds in a clean resolute chroot; details and links in
`research/release-recheck-a/`.

| Package | Newer version checked | Contains our fix? | Answer |
|---|---|---|---|
| cinnamon-session | 6.6.4 (Debian, 26.10); master 6.7-unstable | 6.6.4: none of five. master: 9409c18 (our backport, identical) and cbcc364 (equivalent of "Don't ask a Cinnamon that is not running") | **patch**, 6.4.2-1+unity3 unchanged |
| lightdm | 1.33.1 (Debian), main | no - #484 still open | **patch** |
| unity-settings-daemon | 26.10.1ubuntu.build1 | no - same tree as our base | **patch**, keep our base |
| unity, compiz, unity-session | none exists | - | **patch** |
| gtk-nocsd | 4.8 is the latest | already taken (2026-09-25) | **version** |
| light-locker | 1.9.0 / master | no (decision of 2026-09-23 stands) | **patch** |

**cinnamon-session, and a correction to the reason in CLAUDE.md.** Rule 0 now
cites cinnamon-session as the case where 6.6 "needs a libcinnamon-desktop
26.04 does not have". Measured: 6.6.4-1 as packaged does fail on
`libcinnamon-desktop-dev (>= 6.6)`, but that bound is Debian's ("Bump breaks
and deps to 6.6", 6.6.3-1); upstream's `meson.build` needs `>= 6.0.0`, and with
the bound relaxed to 6.4 it builds in 46 s. So the price of 6.6.4 is one line
in debian/control, not a library. The patch stays for a different reason:
**6.6.4 contains none of our five fixes**, so taking it would add a series'
worth of behaviour change (`cinnamon-session.target` wired to
`graphical-session.target`, next to our login-race fix) and remove nothing.
The version that does contain two of them is master, which is not a release.
The CLAUDE.md sentence is the host's; I have not edited it - May decides.

**Host's sharpest question - does upstream's #214 fix collide with our
inhibitor patch?** No. 9409c18 changes `csm_manager_quit()`/csm-systemd; our
inhibitor patch changes `end_session_or_report_inhibitors()` in the query
phase, which upstream has not touched. Our quit-once guard is still needed
on master (`end_phase()` still re-enters `csm_manager_quit()`, logind answers
OperationInProgress). When we move to a release that contains master:
drop the 9409c18 backport and "Don't ask a Cinnamon...", keep the other three;
do not fuzz "Don't ask..." onto master - it lands in the wrong function.

**lightdm 1.33.1** builds in resolute as Debian packages it (111 s) and has no
liblightdm ABI change, but does not fix #484, so it is not an answer to our
bug. Whether to move to 1.33 for its own sake (user switching fixed, greeter
cancel path changed) is a separate question, not taken here.

**unity-settings-daemon 26.10.1ubuntu** builds too (270 s), but it is our base
plus packaging churn, and its packaging looks broken (plugins installed
outside the path compiled into the daemon - read from the .deb, not run). Not
taken.

**xorg-server** is not patched by us, but the host listed it: 21.1.24-1ubuntu1
from 26.10-proposed builds in resolute unchanged (363 s, same debian/control)
and closes the 11 CVEs open in resolute; it does not contain the #2163497
FindGlyphRef fix. Taking it means carrying the X server in our archive until
Ubuntu ships a security update - for May to decide, the cost is now measured.

Related work found on the way, nothing to take: the Gentoo unity7 overlay
carries an equivalent of our ThumbnailGenerator join fix and different
approaches to the double shutdown dialog and to Nemo; MP 508187 (#2160299)
has two Needs Fixing votes.

## 2026-09-25 - Re-check of agent B's fixes: no newer release has them (agent B)

The host's 02:58Z question for every fix we carry: has a newer version
already fixed it? For agent B's packages, no - every patch stays. Checked
Ubuntu 26.10/stonking (`rmadison`, git-ubuntu trees diffed against ours),
Debian (unstable, experimental) and upstream tags:

- **nux** - our base 0ubuntu15 is itself the newest nux anywhere (26.04 has
  0ubuntu12, 26.10 0ubuntu13, 0ubuntu15 only in stonking-proposed). Neither
  `fix-missing-vidmode.patch` nor `fix-fbo-attachment-arrays.patch`
  (LP #2160298) is in it; gitlab ubuntu-unity/nux head is the same as
  0ubuntu15; MP 508190 is unmerged. Debian has no nux. The only other fix in
  the wild is an untagged fork (Namelus11811/Nux-UnityX 6920ce8f) taking
  riku's approach, which `research/nux-fbo/` rejects.
- **appmenu-gtk-module** - a783b01c (LP #2166410) is on vala-panel-appmenu
  `master` only; the last tag is 25.04. 26.10 ships the same 25.04-1build1,
  Debian 25.04-1.
- **calamares-settings-ubuntu** - 26.10 (1:26.10.4, .5 proposed) leaves
  `basicwallpaper` and `ubuntuunity/oem` untouched; its one OEM change
  (279a0e4) follows 26.10's `pkgselectprocess` and does not apply to 26.04.
- **indicator-bluetooth, -printers, -datetime, -power, -session** - 26.10
  has the same versions as 26.04; no Debian packages; upstream silent since
  2018-2021.
- **indicator-sound** - 26.10's 0ubuntu10 (LP #2166355) is *our* +unity1:
  `git diff origin/ubuntu/devel` against ours is empty outside
  debian/changelog. Nothing to take; renaming ours after it would only
  change the version string.
- **indicator-keyboard** - 26.10's 0ubuntu3 has one of our three changes
  (`lightdm-vala` build-dep). The `systemd-dev` build-dep and the test fix
  (LP #1968333) are ours only. Taking 0ubuntu4 would lose both.

Found on the way: indicator-keyboard 0ubuntu4 in 26.10 ships **no systemd
user unit** - the same break as bluetooth and printers, from the same cause
(build-depends on `systemd`, not `systemd-dev`). Not reported, per May.

No newer version to build, so nothing was measured by sbuild: there is no
candidate. `research/indicator-ftbfs/`, `research/indicator-units/`,
`research/nux-*/`, `research/appmenu-resident/`, `research/calamares-oem/`.

## 2026-09-25 - unity-gtk4-menu 0.9: issue #1's crash is real, and ours (agent B)

Correction to the 2026-09-23 coexistence entry above ("Our shim works in
either load order"): true for the 0.1 shim and Ubuntu's build of gtk-nocsd,
not for 0.8 with gtk-nocsd built by its own `make`. There, most GTK4
applications crashed - in **both** orders, ours included - because
gtk-nocsd's `dlsym` answered `g_module_symbol` with our function (GOT
interposition without `-Bsymbolic-functions`) and we recursed. 0.9 finds the
next definition with glibc's own `dlsym@GLIBC_2.34`; 50 runs, 10 programs, 5
orders, no crash. In aptly, on target2. `research/nocsd-order/`.

## 2026-09-25 - unity-gtk4-menu stays a separate library for now (agent B)

Rule 0, one level up: which existing component was this weighed against?
gtk-nocsd - it hooks the same `g_module_symbol` and `dlsym` paths, its
maintainer says the feature was requested from him (for XFCE) and offers to
build it. Where each wins:

- **gtk-nocsd wins on coverage.** It already handles Gir.Core's raw `dlsym`
  and a statically linked GTK4, which we do not; one library means one set
  of hooks, and issue #1's crash is exactly the cost of two.
- **Ours wins today on existence.** It is written, packaged, and measured
  against the GTK4 applications in `research/layer-b/`; gtk-nocsd has no
  global menu. Its goal is
  removing client-side decorations, which many of its users want without a
  global menu, and in our session order gtk-nocsd would need no change.
- The order dependency is one-sided: with gtk-nocsd first, gjs and Python
  applications silently lose the menu, because gtk-nocsd does not chain
  `g_module_symbol`. Our environment.d order avoids it; nothing enforces it.

Answer: keep the separate library for 26.04, because it works and the
alternative does not exist yet. The better long-term home is gtk-nocsd, if its
maintainer builds the feature: then ours should be retired, not kept in
parallel. That needs the conversation May has put on hold, so it is May's
call; nothing here depends on it being soon.

## 2026-09-25 - unity-gtk4-menu inside gtk-nocsd: works, measured, not taken yet (agent B)

May asked what it takes to stop preloading two libraries and to try it.
Built unity-gtk4-menu 0.9 into our gtk-nocsd 4.8 as a second source file
driven by gtk-nocsd's own constructor, `g_module_symbol()` and `dlsym()`
(`4.8-1+unity2~menu1`, 14 lines added to GTK-NoCSD.c). On target2, installed
session-wide in place of both libraries: session healthy, 18/18 GTK4
applications export the same menus as with two libraries, class-action
stand-ins unchanged, gtk-nocsd's decorations intact, menu stays off outside
Unity. The recursion of issue #1 has nothing left to act on: no
`RTLD_NEXT` remains.

Not taken into aptly: carrying it in our package only moves the duplication
into a 1250-line patch on every gtk-nocsd update. The duplicate ends when
upstream takes the feature (rebase on 4.8+20, a desktop-neutral switch,
upstream's style) - which needs May's go-ahead to talk to the maintainer.
Until then the released pair (gtk-nocsd 4.8-1+unity1 + unity-gtk4-menu 0.9)
stays. `research/nocsd-merge/`.

## 2026-09-25 - global menu as a gtk-nocsd upstream patch: ready, not sent (agent B)

May asked to port the merged menu to gtk-nocsd's current main, make it
desktop-neutral and write it in upstream's style, then decide about talking
to the maintainer. Done as one commit on main 6b1f70a
(`research/nocsd-upstream/`): enabled by GTK's `gtk-shell-shows-menubar`
rather than a desktop list, `GTK_NOCSD_NO_GLOBAL_MENU=1` to disable, written
into `GTK-NoCSD.c` under the README's contribution rules (checked twice by a
separate reviewer, formatted with upstream's Uncrustify config, 0 warnings
under upstream's flags). On target2 session-wide: 18/18 applications with
the same menus as the two-library setup, class-action stand-ins unchanged,
switch correct on bare X, Xfce/KDE (fake flag), GNOME and at runtime.

Not sent: whether and how to offer it is May's call (options in the
research README). aptly still ships gtk-nocsd 4.8-1+unity1 +
unity-gtk4-menu 0.9.

## 2026-09-25 - global menu patch tested under Xfce and Plasma: works, but not out of the box (agent B)

Real Xfce 4.20 (vala-panel-appmenu plugin) and Plasma 6.6.4 X11 (Global Menu
widget, gmenudbusmenuproxy) sessions on target2: with `gtk-shell-shows-menubar`
on, 18/18 applications export the same menus as under Unity and both panels
show and activate them. Neither desktop turns the flag on by itself - Xfce
needs an xfconf key, Plasma a line in `~/.config/gtk-4.0/settings.ini`,
since nothing in Plasma sets it. So the switch is safe everywhere but
effectively Unity-only by default. Enabling also on the presence of
`com.canonical.AppMenu.Registrar` (appmenu-gtk-module's signal) plus hiding
the window's own menubar is the alternative; not built, a design point for
the patch. Also found: under Xfce, Debian's gtk-nocsd `environment.d` does not
reach applications at all. `research/nocsd-desktops/`; target2 back to Clean-2.

## 2026-09-25 - xorg-server 21.1.24 carried in our archive (agent A, May approved)

May chose to carry the X server after the release re-check measured it.
`2:21.1.24-1ubuntu1~26.04.1` is a no-change rebuild of 26.10-proposed's
`21.1.24-1ubuntu1` for resolute: it closes CVE-2026-50256..50264 (21.1.23) and
CVE-2026-55999/56000 (21.1.24), all needs-triage in resolute with no security
upload in sight. The `~26.04.1` suffix keeps it below 26.10's version, so an
upgrade to 26.10 replaces it; there is no `+unity` because nothing in it is ours.

**Verified on target** (VM `target-desktop`): installed with `dpkg -i`
(`xserver-xorg-core`, `xserver-common`, `xserver-xorg-legacy`), rebooted: X
1.21.1.24 up, the same two `(EE)` lines as 21.1.22 (no `vmware` module in
VirtualBox), GLX direct rendering, Unity session, Dash with search, HUD,
workspace switch, spread, an xkb layout switch, window move/resize; three
logout/login cycles through Unity's dialog and a lightdm restart - no crash
files. The `bamfdaemon.service: Failed` lines at logout are old: the same
lines appear in cycles run on 21.1.22 (`~/lo/6`, `n48`, `u1`, `u2` on target).
Then published to aptly; `apt-cache policy` on target shows ours as the candidate.

**The cost we took on:** any resolute security upload built on 21.1.22
(`-1ubuntu1.3` and so on) sorts below ours and will not install while we
carry this. Watch `rmadison xorg-server` for a resolute-security version at
or above 21.1.24, and drop ours then. Not included: the FindGlyphRef crash fix
(LP #2163497, `8d604fa14` on server-21.1-branch, after the 21.1.24 tag) -
not seen in our session, so not patched.

## 2026-09-25 - trial rebuild of section B's never-built sources: libindicator needs a fix, vala-panel is not ours (agent B)

Nine sources nobody had built in resolute, built in a clean `sbuild -d
resolute`: libunity, both lenses, unity-scope-home, indicator-application,
indicator-appmenu and indicator-notifications build. Two do not.

**libindicator** FTBFS: `indicators-pre.target` is no longer installed
(`systemd.pc` moved to `systemd-dev`; systemd was never a declared build-dep),
and `dh_install --fail-missing` stops. The target is load-bearing -
`unity-panel-service` has `BindsTo=indicators-pre.target` - so a rebuild that
only silenced the error would stop the panel service. 26.10 has the same
version, Debian has no libindicator, upstream is dead: patch, not version.
`+unity1` adds `systemd-dev`; built, file lists and exported symbols equal the
archive's. Kept out of aptly: today's archive binary is equivalent, so it goes
in with the first real change to libindicator.

**vala-panel** FTBFS (Debian #1118323, GioUnix-2.0 GIR move); fixed on
upstream master, unreleased. Unity does not use libvalapanel0 - not patched.
`research/rebuild-trial/`.

## 2026-09-25 - xorg-server: our patches on Ubuntu's version, not a newer upstream (agent A, May approved)

Replaces the scheme of the entry above ("xorg-server 21.1.24 carried"). Measured
on target with apt (`research/xorg-versioning/`): `2:21.1.24-1ubuntu1~26.04.1`
outranks every resolute upload Ubuntu can make on 21.1.22, and even a
21.1.24-based `-0ubuntu0.26.04.1`, so it blocked Ubuntu's own security fixes -
a failure worse than stock. No pin fixes that: apt never downgrades an
installed higher version.

Now: `2:21.1.22-1ubuntu1.3+unity1` - Ubuntu's newest resolute upload
(1ubuntu1.3, in -proposed since 2026-09-25, DisplayLink fix only, **no** CVE
patches) plus the 29 upstream commits 21.1.22..21.1.24 as
`debian/patches/upstream-21.1.24/` (all 11 CVEs). Any later Ubuntu upload wins
automatically; ours wins over 1.3 itself, which would otherwise have taken the
fixes away from users when it leaves -proposed (1.2-based was measured to fail
exactly that way). Failure mode now: stock Ubuntu, never worse.

Price: rebase on every new resolute xorg-server. A systemd user timer on
builder (`xorg-watch.timer`, every 3 h) writes one `XORG-WATCH` line to
`~/AGENTS-LOG.md` per new upload, with the days left in -proposed; whoever
sees it tells the coordinator. aptly swapped, target verified (reboot, smoke,
3 logout cycles). xwayland untouched: not installed, not in our session.

## 2026-09-25 - global menu for gtk-nocsd: measurements for the maintainer's second reply (agent B)

Asked through the coordinator, from May. `research/nocsd-reply2/`:

- The holder menu (one panel entry named after the application) opens on
  click in both Unity and Plasma; a flat menubar instead puts every item on
  the panel, overflows it and loses the sections.
- 42 of 44 GTK4 applications export a menu; the two that do not have none to
  export on a fresh profile. 10 items cannot be activated, all from action
  groups inserted on widgets - a gap of the proxy part, not covered.
- GTK3 applications with a header bar menu: our code does nothing to them.
- The patch is split into base / (a) cleaning+proxies / (b) realize / (c)
  setting, any combination builds; measured, (a) takes dead items from 38
  to 2 and (b) adds 7 applications.
- Correction: GTK4's `show-menubar` defaults to FALSE, so exporting without
  the shell flag does not draw a menubar in the window; the earlier
  rationale for (c) was wrong and is corrected.
- Of two unreported gtk-nocsd findings, the gnome-sound-recorder crash is
  fixed by 4.8; the types-never-fetched order reproduces on main.

Nothing was sent; the reply is the coordinator's and May's.

## 2026-09-26 - gtk-nocsd global menu gaps: fixes in parts (a) and (d), Xsession.d script in our package (agent B)

**Context.** May asked (via the coordinator) to dig into the gaps left by
`research/nocsd-reply2/`. Full record: `research/nocsd-gaps/`.

**Decisions.**
- Actions of groups inserted with `gtk_widget_insert_action_group` get
  stand-ins in part (a), by hooking that entry point. Weighed against:
  - appmenu-gtk-module's synthetic `unity.*` actions, which are GTK3 and
    activate widgets;
  - a GTK change to export the muxer, for which no issue exists;
  - leaving the items dead.

  The hook activates the originals with `gtk_widget_activate_action_variant`
  from the widget the group is on, so GTK's own resolution decides. 10 dead
  items become 0 dead items in 44 applications.
- A new part (d) finds menus that appear late and follows menu changes and
  shown menu buttons. It is separate from (a), because the maintainer said he
  would finish the base's search himself, so it is offered as a measurement
  (Pinta 0 to full, Papers and Console now export their real main menu,
  Nautilus Undo follows).
- unity-gtk4-menu 0.9 is not changed: the code belongs in the gtk-nocsd
  parts, not duplicated.
- GTK3, hiding the button and per-window menus are estimated, not built.
- The Xfce `LD_PRELOAD` gap is Debian packaging. Rule 0: no report in the
  Debian BTS, on Launchpad or on Codeberg; systemd#7641 is open; no newer
  gtk-nocsd changes it (4.8-1 is also 26.10's). It is fixed in our package
  as `4.8-1+unity2` with `/etc/X11/Xsession.d/51gtk-nocsd`. A handed the
  package to B for this.

## 2026-09-26 - known issue #1 (pointer invisible after login): cause in u-s-d's idle monitor, patch not version (agent A)

Reproduced on target with real input written into the existing evdev devices:
archive `0ubuntu6` left the pointer hidden in 2 of 12 cold autologins, exactly
the logins where the surviving daemon had lost and regained
`org.gnome.Mutter.IdleMonitor`; `0ubuntu7+unity4` 0 of 12. Cause: the daemon is
started twice (systemd unit + xdg autostart), the two race for that name, and
`on_name_lost` removed the X event filter that drives every idle watch - so the
cursor plugin, which hides the pointer at start, never saw the mouse again.
Proved by re-adding the filter with gdb in a failing session.

Rule 0: gitlab ubuntu-unity issue #161 (open, no cause); LP #1390628 (2014);
26.10's `26.10.1ubuntu` carries the same code; mutter and upstream
gnome-settings-daemon never had this bug (the copy is Ubuntu's, 2014). No
version to take - **patch**: filter installed once at init (mutter's
behaviour), one launcher (unit via `localeexec`, autostart `X-systemd-skip`),
libexecdir restored (our `0ubuntu7` base had broken autostart, `localeexec`
and two polkit actions), and `+unity1`'s cursor change reverted - it was a
guess from the code, and the plugin's hide-until-mouse is fine once its
watches fire. `research/cursor-after-login/`.

## 2026-09-26 - known issue #3 (clicks stop): fixed in Unity's decorations, compiz left as is (agent A)

Reproduced with real device input: a right button (or the wheel) pressed during
a left-button border drag, then any click on a window frame - pointer frozen by
compiz's own synchronous frame grab (unity +unity9: 16 of 50 drag variants;
the release notes' `killall -1 compiz` cleared all). Cause measured with gdb in
compiz: `Edge::ButtonDownEvent` ran again for the second button, its
`XUngrabPointer` stole the running resize's X grab, and the resize's `"resize"`
grab stayed in compiz's list; compiz then skips `XAllowEvents` for frame
grabs. Rule 0: #165 (no cause), LP #1885435 and #1644412 (trigger, no cause),
no fix in any newer compiz or unity.

**Where to fix:** Unity, which broke compiz's assumption that a plugin's X grab
lasts until the plugin releases it. `+unity10` returns early from
`Edge::ButtonDownEvent` while a `"resize"` or `"move"` grab exists: 0 of 50,
resizing unchanged. A compiz hardening (thaw frame grabs even with a leaked
grab) was weighed and not done - it would hide the next leak, not remove it,
and would leave `"resize"` blocking Unity's Super key (LP #1644412). The
#1-related hypothesis (idle monitor, second daemon, lock, suspend, user
switch) was tested and not confirmed. `research/cursor-stops/`.

## 2026-09-26 - indicator-keyboard +unity3 for LP #2166139 (agent B)

**Context.** The coordinator's task B-1: a crash in g_variant_iter_new.

**Rule 0.**
- LP #2166139 has no fix.
- 26.10's 0ubuntu2..4 are rebuilds.
- Ayatana's keyboard indicator is separate C code.

**Decision.** Fix it in our package. The cause is in indicator-keyboard,
which trusted `act_user_get_input_sources()` (transfer none, NULL while
AccountsService has nothing cached) not to return NULL. accountsservice
documents that NULL, so it is not a bug there.

Reproduced by restarting accounts-daemon under the greeter's service:
`+unity2` crashed 3 of 3, `+unity3` survived 3 of 3. Tests pass 10 of 10,
including a new one for NULL. Details: `research/indicator-keyboard-2166139/`.

## 2026-09-26 - indicator-datetime +unity2 for LP #1848969, #2099742 (agent B)

**Context.** The coordinator's task B-2.

**Cause.** A VTODO with only DUE got an unset begin. Its debug message
formatted it anyway and aborted the service. Reproduced on target2 with
`+unity1`.

**Decision.** Fix the cause in our package: place such a task at its DUE,
skip components without a time, and add a test. Weighed against Ayatana's
47e005d (make `DateTime::get()` return NULL). That hides the abort but
passes NULL on and still leaves the task without a time.

Measured: 29 of 29 tests pass; the control build without the fix fails the
new test. Details: `research/indicator-datetime-tasks/`.

#1515821 is intended behaviour (one occurrence per UID) and is left alone.
