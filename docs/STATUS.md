# Status

_Last updated: 2026-09-22_

## Where we are

Bootstrapping. The builder VM is provisioned and the build pipeline is being
brought up for the first time. No package has been built yet, nothing has been
installed on target, no upstream contribution has been made.

Current layer: **A** (keep Unity 7 on X11 alive).

## Done

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
  `website` subgroups. `manifest.repos` written against the real list.
- This meta-repository created, handoff committed first.
- Build chroot built with `mmdebstrap` into
  `~/.cache/sbuild/resolute-amd64.tar.zst` (142 MB, 47 s).
- Pipeline verified: `sbuild -d resolute hello` -> `Status: successful`,
  42 s. `deb-src` had to be enabled by hand first.

## In flight

Nothing. The build pipeline is up and verified.

## Next

1. `vcs import . < manifest.repos` and build `unity` 7.7.1 for resolute.
   Record in DECISIONS.md how healthy the code actually is - what breaks, what
   warns, how long it takes.
2. Pick one known 26.04 bug, reproduce it on target, fix it, build it, verify
   with a screenshot, send it upstream as a merge request.
3. Stand up `aptly` and publish over the host-only interface so target can
   `apt install` from it.
4. Resolve where `vala-appmenu-panel` actually is. The 26.04 release notes say
   the global menu moved to it; it is not on target, not in the archive and not
   in the upstream group. Layer B needs the answer.

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
