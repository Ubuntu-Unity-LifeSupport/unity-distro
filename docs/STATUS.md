# Status

_Last updated: 2026-09-23_

## Where we are

Bootstrapping. The builder VM is provisioned and the build pipeline is being
brought up for the first time. No package has been built yet, nothing has been
installed on target, no upstream contribution has been made.

Current layer: **A** (keep Unity 7 on X11 alive).

## Done

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

0. **Layer B is bigger than planned: Qt has no global menu in 26.04 at all.**
   `appmenu-qt5` does not exist in the archive. GTK4 is covered by our shim,
   GTK3 by the existing `appmenu-gtk-module`, and Qt needs building from
   nothing - most likely a Qt platform theme exporting through dbusmenu, as KDE
   does. Not started; recorded so it is not mistaken for a small item.
1. **Layer B: widget-scoped actions.** Breadth on real applications is
   measured and 0.3 is published. The known gap is actions registered with
   `gtk_widget_insert_action_group()` on a sub-widget - they are not in the
   window's exported group, so their menu items arrive insensitive. yelp's
   "О приложении" is the reproducer. See `research/layer-b/`.
2. **Next Layer A candidate: the shutdown path.** Known issues #2 (menu stops
   responding after cancelling) and #6 (double confirmation dialog). Measured
   2026-09-23: **there are two different shutdown dialogs** on target. The
   session indicator's "Выключение..." opens Unity's own ("До скорой встречи,
   Mike"); the power key opens `cinnamon-session-quit`'s ("Выключить систему
   сейчас?"). Two components, two dialogs - a strong lead for #6, not yet a
   proof that they ever appear together. Also: `unity-settings-daemon` and
   `cinnamon-settings-daemon` both run and disagree on the power button
   (`interactive` versus `suspend`). Start in the Cinnamon layer, not in Unity.
   See `ARCHITECTURE.md`.
3. Pick a second contribution candidate. `light-locker` crashing on login is
   the obvious one: documented, reproducible, and still present after every
   pending update.
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
| 2 | Shutdown/logout menu unresponsive **after cancelling** | tty + `sudo poweroff` |
| 3 | Cursor stops responding | `killall -1 compiz` |
| 4 | Wallpaper over the Calamares window during OEM install | Alt+Tab to the installer |
| 5 | light-locker crashes on login, login still works | - |
| 6 | Shutdown confirmation dialog appears twice | disabled through gsettings |

Bug 3's workaround - a signal to compiz - suggests the input handling loop
rather than performance, which the handoff's "cursor lags" had obscured.

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
