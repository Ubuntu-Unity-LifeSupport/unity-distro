# Status

_Last updated: 2026-09-23_

## Where we are

Layer A is producing fixes; Layer B has a packaged GTK4 global menu. Three
Layer A contributions are queued in `docs/upstream/`, none sent: `nux-pcre2`,
`light-locker-session`, `unity-stale-pending-action`. Our aptly repository
carries nux 0ubuntu15+unity2, calamares-settings-ubuntu 1:26.04.12+unity1, light-locker `+unity2`, unity `+unity2` and
unity-gtk4-menu 0.9.

Current layer: **A** (keep Unity 7 on X11 alive).

## Done

- **indicator-keyboard tests run again (LP #1968333, open since 2022).**
  The crash was in the test's mock, not the service: Vala >= 0.55.1
  compiles a detailed `notify` emission to `g_object_notify (self, pspec)`.
  Fixed the mock, made test failures fatal again; 9/9 pass (+unity2, in
  aptly). Vala bug and LP fix wait for May. `research/indicator-ftbfs/`.
- **Five indicators build again in resolute.** datetime, power, session,
  sound and keyboard failed to build (CMake 4, GCC 15, libnotify 0.8 in a
  test, moved build-deps); rebuilt as +unity1, same files as the archive, in
  aptly and running on target2.
  `research/indicator-ftbfs/`.
- **appmenu-gtk3-module made resident (LP #2166410).** Upstream's fix
  carried as 25.04-1build1+unity1, in aptly. The crash needs the module to
  come from the `gtk-modules` setting (KDE); our session loads it through
  `GTK_MODULES`, which GTK3 never unloads - so this is protection, not a fix
  for something users of our session hit. `research/appmenu-resident/`.
- **nux 0ubuntu15+unity2: LP #2160298 fixed.** FBO attachment vectors were
  indexed while empty - an abort under `_GLIBCXX_ASSERTIONS` and a texture
  reference leak in the package we shipped. Proven with a small test, fixed,
  in aptly; Unity's tests pass against it. `research/nux-fbo/`.
- **indicator-bluetooth and indicator-printers start again.** The 26.04
  rebuild lost their systemd user units (found by the stack-health sweep);
  rebuilt with `systemd-dev`, `+unity1` in aptly, both services running on
  target2. `research/indicator-units/`.
- **Login race fixed: black desktop for two minutes after some logins.**
  unity-session's `run-systemd-session` stopped graphical-session.target at
  every login, even when it was not running, killing gvfs-daemon while
  ibus-daemon was activating it; dbus-daemon then waited 120 s. 3 logins in 13
  on target; 0 in 6 with unity-session `49.4+unity1` (in aptly).
  `research/login-gvfs-race/`. Logout with unity `+unity8`/compiz `+unity2`
  measured clean in six cycles (`research/compiz-restart/`).

- **Restarting compiz (`killall -1 compiz`, the #3 workaround) fixed.** The
  release notes' side bug is real: every restart moved windows on lower
  workspaces up by a title bar until they landed on the first row (compiz
  core, workarea clamp of the current viewport; compiz `+unity2`). Behind it:
  compiz segfaulted on every exit (Unity `ThumbnailGenerator`), unfocused
  windows lost their title bars after a restart (Unity decorations vs Yaru's
  0 px inactive shadow; unity `+unity8`), and gtk-nocsd's crash handler
  crashed at every crash of a preloaded program (two upstream backports;
  gtk-nocsd `+unity2`). All three in aptly, verified on target over five
  restarts on a 2x2 workspace grid. `research/compiz-restart/`.

- **gtk-nocsd 4.8 (LP #2158965).** Chromium browsers lost their window
  buttons under Unity; resolute's March snapshot empties the decoration
  layout Chromium reads. Rebased on Debian 4.8-1 as `4.8-1+unity1` (our two
  crash-handler backports are part of it). Chrome has its buttons, 13 GTK
  applications A/B-tested without regressions, gnome-sound-recorder no longer
  crashes, crash handler and compiz restart work. In aptly.
  `research/gtk-nocsd-4.8/`.

- **Known issue #4 (wallpaper over Calamares) fixed.** It is the OEM
  first-time setup session, not the vendor's install: xfwm4 raises the
  focused fullscreen `basicwallpaper` window above Calamares, after a startup
  race or on Alt+Tab. `basicwallpaper` is now a desktop window that takes no
  focus. calamares-settings-ubuntu 1:26.04.12+unity1 in aptly; matters for
  our ISO only. Confirmed on a real two-stage OEM install from the official
  ISO (VM `oem-test`): the archive binary hid Calamares on 3 of 3 cold
  first boots of the end user's session, ours on 0 of 2; the setup ran
  through.
  `research/calamares-oem/`.
- **Known issue #2 fixed in Unity, and a worse bug found behind it.** One
  cause: Unity records a pending end-session action and waits for the session
  manager to call `EndSessionDialog.Open` back; cinnamon-session never does, so
  after its own dialog is cancelled the action stays pending. Pending
  `SHUTDOWN` makes the session menu dead (#2). Pending `REBOOT` - found while
  testing the first fix - makes the next "Выключение..." click restart the
  machine at once with no dialog: Unity takes the indicator's request as the
  confirmation and indicator-session calls logind. Reproduced on the archive
  package. Fix: only the owner of `org.gnome.SessionManager` may confirm.
  `unity +unity2`, two new unit tests (the suite had to be revived to run on
  26.04 - three separate breakages, see DECISIONS), both symptoms verified
  fixed on target with screenshots and bus logs. Queued in
  `docs/upstream/unity-stale-pending-action/`; package repository
  https://github.com/Ubuntu-Unity-LifeSupport/unity.

- **Layer A's first fix of our own: light-locker no longer crashes on login.**
  Known 26.04 issue #5. Two stacked aborts with one cause - light-locker is
  started by cinnamon-session, which runs as the systemd user service
  `unity-session.service`, so it sits outside the logind session scope and
  inherits neither a session nor LightDM's `XDG_SESSION_PATH`. Two patches,
  built as `1.8.0-3ubuntu4+unity2`, verified on a clean desktop: alive after
  login, owns the ScreenSaver name, and actually locks - the greeter comes up
  in unlock mode. Unlock verified by hand by May, corroborated by the LightDM
  log. No untested step remains. Queued in `docs/upstream/light-locker-session/`, repository
  https://github.com/Ubuntu-Unity-LifeSupport/light-locker.

- **Layer B has a working, packaged global menu for GTK4.** `unity-gtk4-menu`
  0.2, its own repository at
  https://github.com/Ubuntu-Unity-LifeSupport/unity-gtk4-menu, built in a clean
  chroot, published to the local archive and installed on target. A GTK4
  header bar menu appears in the Unity panel and is searchable in the HUD, with
  no patch to GTK4, libadwaita or any Ubuntu package. Path there, all measured
  and recorded in `research/layer-b/`:
  - GTK4 has no module loading mechanism, so `appmenu-gtk-module` cannot be
    extended to it; `LD_PRELOAD` plus overwriting `realize` in the class
    vtable is the route, and `gtk-nocsd` already ships that technique in
    Ubuntu Unity.
  - Stock GTK4 still exports a menubar and Unity renders it; the menubar must
    be set before realize.
  - The menubar route was chosen over `_GTK_APP_MENU_OBJECT_PATH`: it matches
    what `appmenu-gtk-module` does, the HUD covers it with better context, and
    Ubuntu once patched app menus away.
  - The top-level label is a GSettings preference,
    `com.ubuntu-unity.gtk4-menu show-application-name`.
  - Version 0.1 linked GTK4 and, installed session-wide, killed GTK3
    processes. 0.2 links nothing but libc, resolves every symbol with `dlsym`,
    and does nothing unless GTK4 is already mapped. `make check` fails the
    build if GTK or GLib reappears in `NEEDED`.

- **Layer B scoped by experiment, not by assumption.** Stock GTK4 exports a
  menubar and the Unity panel displays it - proven with a minimal GTK4
  application. GTK4 has no module mechanism, so `appmenu-gtk-module` cannot be
  extended to it, and the menubar has to be set before window realize. See
  `research/layer-b/`.
- **`nux` verified end to end from a clean target.** Rolled back to
  `Clean-updated-2026-09-23`, added the repository, installed with one `apt`
  command, rebooted into a session that came up by itself, and ran the whole UI
  checklist. This is the evidence the SRU test plan describes; every earlier
  install went through `scp` and `dpkg -i`, which tests the package but not the
  delivery path.
- **Local apt repository is up.** aptly at `/srv/aptly`, signed, served by
  nginx on `192.168.56.10:8080` and bound to that address only. Proven end to
  end: target's apt fetched `libnux-4.0-0` and `libnux-4.0-common` from
  `http://192.168.56.10:8080` and installed them. Only `nux` 0ubuntu13 is
  published - see `repo/README.md` for why our `unity` build is not.
- **`nux` `-0ubuntu13` verified on target.** Installed over the archive's
  `-0ubuntu12`, rebooted, full UI checklist passed, no crashes, compiz maps
  `libpcre2-8` and no PCRE1.
- **`unity` 7.7.1 builds for resolute.** Seven binary packages, 372 s on four
  cores, against a locally built `nux` `-0ubuntu13`. 746 compiler warnings,
  mostly `-Wtemplate-id-cdtor`; dated but not broken.

- `builder` surveyed and provisioned: Ubuntu 26.04.1 (resolute), 4 cores,
  8 GB RAM, root filesystem grown from 97 GB to 195 GB with `lvextend` +
  `resize2fs` (the volume group had 99 GB unallocated; VirtualBox untouched).
- Build tooling installed: `sbuild`, `schroot`, `debootstrap`, `mmdebstrap`,
  `git-buildpackage`, `devscripts`, `ubuntu-dev-tools`, `git-ubuntu`, `aptly`,
  `quilt`, `tmux`, `vcstool`.
- `ssh target` verified. Screenshot pipeline verified end to end without sudo
  (`gnome-screenshot` on target, fetched with `scp`). First capture kept at
  `docs/screenshots/2026-09-22-target-unity-desktop.png`: panel, launcher,
  indicators, global menu and wallpaper all render correctly.
- Upstream group inventoried: 28 projects across `unity`, `lomiri` and
  `website` subgroups. `manifest.repos` written against the real list, and all
  eight repositories imported with `vcs import`.
- This meta-repository created, handoff committed first.
- Build chroot built with `mmdebstrap` into
  `~/.cache/sbuild/resolute-amd64.tar.zst` (142 MB, 47 s).
- Pipeline verified: `sbuild -d resolute hello` -> `Status: successful`,
  42 s. `deb-src` had to be enabled by hand first.

## In flight

**Layer B is packaged and running on target; Layer A's first contribution is
queued.**

**Layer A is unblocked and the fix is verified on hardware.**

`unity` 7.7.1 builds against a locally built `nux` `-0ubuntu13`, and that nux
is installed and running on target with no regression: Dash, HUD, indicators,
shutdown menu, decorations and wallpaper all work, and compiz has
`libpcre2-8` mapped with no PCRE1 anywhere. Full checklist in DECISIONS.md.

Getting `-0ubuntu13` into resolute is a process problem rather than a technical
one, and it is **deliberately on hold** - see below.

**What blocks the upload.** LP: #2147013 is marked *Fix Released* because the
Launchpad Janitor closes a bug when the package publishes in the *development*
series; `-0ubuntu13` published in stonking, so the bug snapped shut. From
26.04's point of view nothing was fixed. The upload to resolute-proposed on
2026-04-24 was deleted four days later by Timo Aaltonen with the reason "SRU
cleanup" - the day after 26.04 released, so it was almost certainly swept up as
not following SRU process.

So there is nothing sitting in proposed to verify. It needs a fresh upload,
filed properly as an SRU.

**Held by May's decision, 2026-09-23.** Not from doubt about the work: a first
approach to an unfamiliar team is worth doing calmly rather than in passing.
This does not block anything. The fixed packages go to our own aptly repository
and onto target, so we have a working 26.04 regardless of the archive.

The submission is written and waiting in
[`docs/upstream/nux-pcre2/`](upstream/nux-pcre2/): bug comment, all four SRU
sections, seven evidence files and a re-check list. Nothing is sent until May
reads the specific text and agrees.

## Next

0. _(resolved 2026-09-24, agent B)_ **Qt needs nothing: its global menu
   already works.** The old item said Qt had none because `appmenu-qt5` is
   gone; Qt 5.7+ exports its menubar itself through
   `com.canonical.AppMenu.Registrar`, which unity-panel-service provides.
   Measured with Qt5, Qt6 and KDE applications: panel, activation, HUD. See
   `research/layer-b/` and DECISIONS 2026-09-24.
1. **Layer B: unity-gtk4-menu 0.9 released (agent B).** 0.4 proxies class
   actions, 0.5 exports the main menu rather than the first menu button, 0.6
   reaches gjs and Python applications through `g_module_symbol()`, 0.7 makes
   stand-ins follow the application's enabled state (and so `hidden-when`),
   0.8 proxies property actions as check and radio items, 0.9 stops a
   recursion crash next to a gtk-nocsd built by its own `make` (issue #1,
   `research/nocsd-order/`).
   Over 21 GTK4 applications (15 C, 3 gjs, 3 Python), every one that has a
   menu exports its main menu with no dead item and correct sensitivity -
   except gnome-sound-recorder, which gtk-nocsd crashes with or without us;
   verified installed session-wide after reboot, published to aptly. The
   "menus built after realize" item was a misdiagnosis: font-viewer has no
   menu, contacts shows a setup window first and 0.7 already exports its main
   menu. Nothing open in the package itself. Found on the
   way, not ours: two gtk-nocsd bugs (DECISIONS 2026-09-24; reporting upstream
   is May's call). See `research/layer-b/`.
2. **Layer A: #6, the double dialog - fixed in our archive (2026-09-24).**
   unity `+unity4`, cinnamon-session `+unity1` (option A) and compiz `+unity1`
   (exit race) published together and verified from a clean snapshot via apt:
   one dialog on every path, inhibitors shown, no compiz exit crash. Upstream
   drafts not written yet. The "two settings daemons disagree on the
   power button" item was a measurement error: `cinnamon-settings-daemon`
   does not run under Unity (DECISIONS 2026-09-24). Details in
   `docs/status/A.md` and `research/shutdown-path/`.
3. **Small upstream items found on the way, not queued:** Unity's unit tests
   do not build on 26.04 (C++14 vs googletest 1.17, GCC 15 in
   `tests/gmockvolume.c`); nux crashes without XF86VidMode
   (`GraphicsDisplayX11.cpp:297`) - _fixed in nux 0ubuntu13+unity1 by agent B,
   carried to 0ubuntu15+unity1 (upstream rebase) and in aptly; Unity's unit tests now run under plain Xvfb. See
   `research/nux-vidmode/`_; nux `Validator::Validate`; Vala >= 0.55.1
   drops the detail of an emitter signal emission (`notify["x"] (pspec)` ->
   `g_object_notify (self, pspec)`), and our indicator-keyboard fix for
   LP #1968333 (`research/indicator-ftbfs/`). See DECISIONS and PATCHES.
4. _(resolved 2026-09-22)_ The component is `vala-panel-appmenu`, not
   `vala-appmenu-panel` - the handoff transposed the words. Upstream is
   https://gitlab.com/vala-panel-project/vala-panel-appmenu. Ubuntu splits that
   tree into `src:appmenu-gtk-module`, `src:appmenu-registrar` and
   `src:vala-panel-appmenu`; Unity uses the first two. The binary package named
   `vala-panel-appmenu` only carries plugins for the Xfce, MATE and vala-panel
   shells, which is why it is not installed on target.

## Known bugs in Ubuntu Unity 26.04 (candidates for the first contribution)

Six, from the release notes, with their workarounds - the workarounds point at
the mechanism better than the symptoms do. Corrected list as of 2026-09-23; the
handoff originally had five and had dropped a precondition.

| # | Bug | Release-note workaround |
|---|---|---|
| 1 | Cursor disappears after login | `sudo systemctl restart lightdm` |
| 2 | Shutdown/logout menu unresponsive **after cancelling** | tty + `sudo poweroff` - **fixed in our unity +unity2** |
| 3 | Cursor stops responding | `killall -1 compiz` - not reproduced; the workaround itself crashed compiz and walked windows off the lower workspaces, **fixed in unity +unity8, compiz +unity2** (`research/compiz-restart/`) |
| 4 | Wallpaper over the Calamares window during OEM install | Alt+Tab to the installer - **fixed in our calamares-settings-ubuntu +unity1** (`research/calamares-oem/`) |
| 5 | light-locker crashes on login, login still works | - |
| 6 | Shutdown confirmation dialog appears twice | disabled through gsettings |

Bug 3's workaround - a signal to compiz - suggests the input handling loop
rather than performance, which the handoff's "cursor lags" had obscured.

**Update 2026-09-23: #2 and #6 both reproduced.** The 2026-09-22 attempt
below cancelled Unity's dialog; the precondition is cancelling the *second*
dialog, cinnamon-session's, after confirming Unity's. The double dialog's
mechanism is proven end to end. Both in `research/shutdown-path/`.

**Shutdown menu, tested 2026-09-22 - not reproduced.** The first attempt tested
the wrong thing: the note says the menu fails *after cancelling*, and opening it
once only shows the state before the bug can occur. Retested properly - open the
dialog, cancel, try again - with both cancel routes, `Escape` and the close
cross, since the dialog has no Cancel button. The menu opened and the dialog
reappeared every time. The logout path is still untested.

Not reproduced is not disproved. It stays a live candidate until someone finds
the missing precondition or the team confirms it is gone.

**`light-locker` crashing is a documented known issue**, not a new find:
"light-locker seems to crash on login but login works; there are seemingly no
side effects". We saw it twice, before and after our changes, and kept a dump in
`~/evidence/` on builder. If anyone picks it up, the first question is whether
"no side effects" is actually true.

_Retracted 2026-09-22: we briefly listed "no wallpaper on target" as a sixth
item. It was an artefact of capturing the X11 root window under a compositor,
not a bug. See DECISIONS.md._

## Rules for going upstream

Written up in `docs/CONTRIBUTING-UPSTREAM.md`, summarised in `CLAUDE.md`, and
available as the `upstream-contribution` skill. Read it before preparing
anything that leaves this machine. Nothing goes out without May's agreement,
and `Signed-off-by` is his alone.

## Blocked / needs May

Nothing blocking right now.

Deferred: builder RAM can go from 8 GB to 16 GB
(`VBoxManage modifyvm builder-server --memory 16384`) at the next natural
shutdown. CPU stays at 4 - the host has 8 physical cores and 11 vCPU are
already handed out.
