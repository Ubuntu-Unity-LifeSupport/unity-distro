# Architecture

## What Unity 7 actually is

| Component | Role | Source |
|---|---|---|
| Compiz | window manager and compositor, X11 only | Ubuntu archive |
| Nux | Unity's own OpenGL toolkit, draws the shell | `ubuntu-unity/unity/nux` |
| `unity` | the shell itself: launcher, panel, Dash, HUD | `ubuntu-unity/unity/unity` |
| BAMF | matches windows to applications | Ubuntu archive |
| indicators | panel applets (network, sound, session, ...) | Ubuntu archive + `unity-indicators` |
| `appmenu-gtk3-module` | strips menu bars out of GTK3 apps and exports them | Ubuntu archive |
| `unity-settings-daemon`, `unity-control-center` | settings | upstream group |
| `unity-greeter` | login screen | upstream group |

The upstream group also carries the Dash scopes and lenses, `yaru-unity7`,
a Plymouth theme, and a separate `lomiri` subgroup that is not our concern.

## Layer A - keep Unity 7 on X11 alive

Fix the build against current Ubuntu, close known 26.04 bugs, keep GTK4 and
libadwaita window decorations working. Send everything upstream.

Lifespan of this path: as long as `xserver-xorg` stays in the archive and GTK
and Qt keep their X11 backends. GTK5 will not have one. Estimate: 2-4 years.

## Layer B - the patched stack

The interesting problem. GTK4 and libadwaita applications have no menu bar -
they carry a hamburger button holding a `GMenuModel` inside a popover.

The machinery to export a menu over D-Bus already exists in GTK4
(`org.gtk.Menus`, `gtk_application_set_menubar`). What is missing is a patch
that exports the menu models of popovers, `GtkMenuButton` and `AdwHeaderBar`,
and registers them through `com.canonical.AppMenu.Registrar`.

One such patch gives the global menu and the HUD to every libadwaita
application at once. It is the most valuable and the longest-lived work in the
project: both the X11 Unity and any future Wayland Unity need it.

Also in this layer: `appmenu-gtk-module` for GTK3, `appmenu-qt5` and a Qt6
equivalent, and whatever is left of menu export in Firefox, Chromium,
LibreOffice and Thunderbird.

### What the menu stack on target actually is

Verified by inspecting the installed packages on target, 2026-09-22:

| Package | Version | Role |
|---|---|---|
| `appmenu-gtk3-module` | 25.04-1build1 | exports GTK3 menu bars over D-Bus |
| `libappmenu-gtk3-parser0` | 25.04-1build1 | GtkMenuShell to GMenuModel parser |
| `appmenu-registrar` | 25.04-1build1 | `com.canonical.AppMenu.Registrar` |
| `indicator-appmenu` | 15.02.0+20.10.20260311-0ubuntu1 | the panel-side menu indicator |

Two corrections to the handoff fall out of this:

- **`unity-gtk-module` is not installed at all.** The GTK3 path runs on
  `appmenu-gtk-module`. That is the tree to patch, not `unity-gtk-module`.
- **`vala-appmenu-panel` is nowhere to be found** - not on target, not in the
  Ubuntu archive, not in the upstream GitLab group. The 26.04 release notes say
  the project moved to it for the global menu, but the running system does not
  use it. Either it was reverted before release or it lives somewhere not yet
  located. Worth resolving before Layer B starts, since the component would sit
  right in the middle of it.

All of it as quilt series in `debian/patches/` on top of the Ubuntu packages,
versioned `+unity1`. Never a wholesale fork of GTK.

## Layer C - Unity on Wayland

Replace Compiz and Nux. Leading candidate is **Wayfire**, written with an eye
on Compiz and already carrying expo, scale, cube and wobbly plugins. The shell
- launcher, panel, Dash, HUD, indicators - would be GTK4 with
`gtk4-layer-shell`.

Ayatana indicators already run on Wayland in the MATE and Lomiri panels. The
global menu travels over the KDE appmenu D-Bus protocol
(`com.canonical.AppMenu.Registrar` plus dbusmenu), which works under Wayland
for Qt and GTK3; GTK4 needs the Layer B patch.

A first version is person-months. Parity with Unity 7 including Dash scopes is
person-years. Not to be started before A and B produce results.

## Build pipeline

```
manifest.repos  --vcstool-->  packages/*  --sbuild-->  .deb  --aptly-->  apt repo
                                                                            |
                                                             target installs over host-only
```

`sbuild` runs in unshare mode against `~/.cache/sbuild/resolute-amd64.tar.zst`.
Publishing outward later means either a Launchpad PPA or the same sbuild+aptly
under GitLab CI; the sources and the result are identical either way.
