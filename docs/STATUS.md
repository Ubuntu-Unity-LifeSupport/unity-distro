# Status

_Last updated: 2026-09-22_

## Where we are

Bootstrapping. The builder VM is provisioned and the build pipeline is being
brought up for the first time. No package has been built yet, nothing has been
installed on target, no upstream contribution has been made.

Current layer: **A** (keep Unity 7 on X11 alive).

## Done

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

**Layer A is unblocked. `unity` 7.7.1 builds.**

The blocker was `nux-4.0.pc` advertising PCRE1, which resolute no longer has.
The fix was already written upstream but stopped one revision short of the
archive: `-0ubuntu12` (in resolute) ports the code, `-0ubuntu13` adds the
`.pc` and `configure.ac` hunks and was never uploaded. Built `-0ubuntu13`
ourselves and `unity` now compiles against it. Full history in DECISIONS.md.

Nothing is blocked right now.

## Next

1. Get `nux` `-0ubuntu13` into resolute. The patch is written, the bug exists
   (LP: #2147013), and we can now demonstrate the whole chain: `-0ubuntu12`
   breaks `unity`, `-0ubuntu13` fixes it, `unity` builds. This is the first
   contribution.
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
