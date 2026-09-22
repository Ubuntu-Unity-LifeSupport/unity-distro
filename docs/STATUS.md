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
  (`xwd` on target, converted with ImageMagick on builder).
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

## Known bugs in Ubuntu Unity 26.04 (candidates for the first contribution)

From the release notes, not yet reproduced by us:

- cursor disappears after login
- shutdown / logout menu does not work
- cursor lags under Compiz
- wallpaper wrong after an OEM install
- shutdown dialog appears twice

Observed by us on target on 2026-09-22: the desktop has **no wallpaper at all**,
just black. Panel, launcher and indicators render correctly. Possibly the same
bug as the OEM wallpaper one, not yet investigated.

## Blocked / needs May

Nothing blocking right now.

Deferred: builder RAM can go from 8 GB to 16 GB
(`VBoxManage modifyvm builder-server --memory 16384`) at the next natural
shutdown. CPU stays at 4 - the host has 8 physical cores and 11 vCPU are
already handed out.
