# unity-distro

A patched Ubuntu with the Unity desktop, where the global menu and the HUD work
across the whole stack - not only in the shell, but in the system libraries and
the major applications, the way Canonical shipped it in the Unity 7 era.

Long term goal: a Unity that survives the end of X11.

## Why

Ubuntu Unity 26.04 shipped in April 2026 with Unity 7.7.1, rebuilt by a new
volunteer team after the project nearly died in late 2025. It works, but the
team is short on hands and the known bugs are piling up. Meanwhile Ubuntu's
main GNOME edition went Wayland-only, and modern GTK4/libadwaita applications
have no menu bar to export at all.

This repository is the plan and the build pipeline for keeping Unity alive and
then moving it forward.

## Three layers, worked in order

| Layer | What | Status |
|---|---|---|
| **A** | Keep Unity 7 on X11 alive: fix the build for current Ubuntu, close known 26.04 bugs, send fixes upstream | active |
| **B** | The patched stack: export menu models from GTK4/libadwaita, GTK3, Qt5/Qt6 and the major apps so the global menu and HUD work everywhere | not started |
| **C** | Unity on Wayland: replace Compiz+Nux, likely with Wayfire plus a GTK4 shell | not started |

Upstream first: anything that can land in `gitlab.com/ubuntu-unity` goes there
as a merge request rather than staying a fork.

## Layout

```
manifest.repos      vcstool manifest of upstream Unity sources
series.yaml         which Ubuntu series we build for
build/              sbuild configuration and build order
repo/               aptly configuration, publishing scripts
iso/                live-build image configuration (later)
docs/               STATUS, DECISIONS, ARCHITECTURE, PATCHES, TESTING
packages/           package sources, imported with vcstool (gitignored)
```

## Getting the sources

```bash
pipx install vcstool && pipx inject vcstool 'setuptools<81'
vcs import . < manifest.repos
```

Start with [docs/STATUS.md](docs/STATUS.md) for the current front of work, and
[UNITY-DISTRO-HANDOFF.md](UNITY-DISTRO-HANDOFF.md) for the full project brief.
