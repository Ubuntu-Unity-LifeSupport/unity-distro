# Status

_Last updated: 2026-09-22_

## Where we are

Bootstrapping. The builder VM is provisioned and the build pipeline is being
brought up for the first time. No package has been built yet, nothing has been
installed on target, no upstream contribution has been made.

Current layer: **A** (keep Unity 7 on X11 alive).

## Done

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

**Layer A is unblocked and the fix is verified on hardware.**

`unity` 7.7.1 builds against a locally built `nux` `-0ubuntu13`, and that nux
is installed and running on target with no regression: Dash, HUD, indicators,
shutdown menu, decorations and wallpaper all work, and compiz has
`libpcre2-8` mapped with no PCRE1 anywhere. Full checklist in DECISIONS.md.

The one thing left is getting `-0ubuntu13` into resolute, and that is a
process problem rather than a technical one - see below.

**What blocks the upload.** LP: #2147013 is marked *Fix Released* because the
Launchpad Janitor closes a bug when the package publishes in the *development*
series; `-0ubuntu13` published in stonking, so the bug snapped shut. From
26.04's point of view nothing was fixed. The upload to resolute-proposed on
2026-04-24 was deleted four days later by Timo Aaltonen with the reason "SRU
cleanup" - the day after 26.04 released, so it was almost certainly swept up as
not following SRU process.

So there is nothing sitting in proposed to verify. It needs a fresh upload,
filed properly as an SRU.

## Next

1. **Run the SRU for `nux` `-0ubuntu13`.** Needs May's approval first - it is
   outward-facing and goes out under his name. Steps: nominate LP: #2147013 for
   the Resolute series (there is no Resolute task at all right now, so the bug
   is invisible to the SRU team), post an SRU-template comment, and note that
   the earlier upload was deleted as "SRU cleanup" so nobody re-treads it.
   Impact / Test Plan / Regression potential are all written up in
   DECISIONS.md already.
2. Pick one known 26.04 bug, reproduce it on target, fix it, build it, verify
   with a screenshot, send it upstream as a merge request.
3. Stand up `aptly` and publish over the host-only interface so target can
   `apt install` from it.
4. _(resolved 2026-09-22)_ The component is `vala-panel-appmenu`, not
   `vala-appmenu-panel` - the handoff transposed the words. Upstream is
   https://gitlab.com/vala-panel-project/vala-panel-appmenu. Ubuntu splits that
   tree into `src:appmenu-gtk-module`, `src:appmenu-registrar` and
   `src:vala-panel-appmenu`; Unity uses the first two. The binary package named
   `vala-panel-appmenu` only carries plugins for the Xfce, MATE and vala-panel
   shells, which is why it is not installed on target.

## Known bugs in Ubuntu Unity 26.04 (candidates for the first contribution)

From the release notes, not yet reproduced by us:

- cursor disappears after login
- shutdown / logout menu does not work
- cursor lags under Compiz
- wallpaper wrong after an OEM install
- shutdown dialog appears twice

None of these has been reproduced by us yet.

_Retracted 2026-09-22: we briefly listed "no wallpaper on target" as a sixth
item. It was an artefact of capturing the X11 root window under a compositor,
not a bug. See DECISIONS.md._

## Blocked / needs May

Nothing blocking right now.

Deferred: builder RAM can go from 8 GB to 16 GB
(`VBoxManage modifyvm builder-server --memory 16384`) at the next natural
shutdown. CPU stays at 4 - the host has 8 physical cores and 11 vCPU are
already handed out.
