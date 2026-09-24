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

**In 26.04 there is a Cinnamon layer between Unity 7 and systemd**, and the
table above is only half the picture. `unity-session` 49.4 depends on
`cinnamon-session`, `cinnamon-settings-daemon` and `cinnamon-common`, and its
user unit runs `cinnamon-session --session=unity`:

```
systemd --user
 └─ unity-session.service    cinnamon-session --session=unity
     ├─ launches /etc/xdg/autostart entries itself, as its own children
     └─ ...
 └─ unity7.service           compiz
 └─ unity-panel-service.service
```

`cinnamon-settings-daemon` is installed (`unity-session` depends on it) but
**does not run** in a Unity session: every `csd-*` autostart entry says
`OnlyShowIn=X-Cinnamon;`, the session is `Unity:Unity7:ubuntu`, and
`unity.session` requires only `unity-settings-daemon`. *(Corrected
2026-09-24. This paragraph used to say both were running; that came from
`pgrep -cf cinnamon-settings-daemon` run through `bash -c`, which counted its
own command line.)* This layer is
recent and maintained: `unity-session` is the most recently changed repository
in the upstream group.

It explains several things at once:

- why session processes live outside the logind session scope - their parent
  is `cinnamon-session`, a user service, not LightDM; that is the root of the
  light-locker crash
- why autostart entries bypass systemd's generator and its `NotShowIn`
  handling - `cinnamon-session` launches them itself
- the shutdown path has **two dialogs from two components**, measured
  2026-09-23:

  | Trigger | Dialog | Owner |
  |---|---|---|
  | session indicator, "Выключение..." | "До скорой встречи, Mike", restart/power icons | Unity |
  | power key | "Выключить систему сейчас?", Suspend / Cancel / Restart / Shut down | `cinnamon-session-quit`, in `unity-session.service` |

  The power key reaches `cinnamon-session-quit` because `unity-settings-daemon`
  holds a blocking logind inhibitor on `handle-power-key` and its action is
  `interactive`. (`org.cinnamon.settings-daemon.plugins.power button-power`
  says `suspend`, but nothing reads it - `csd-power` does not run.) Two
  shutdown dialogs coexisting made the Cinnamon layer the first suspect for
  the shutdown menu and double-dialog known issues - rightly, see
  `research/shutdown-path/`. Since cinnamon-session `+unity1` the power key
  shows Unity's dialog too.

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

**Measured 2026-09-23, and it changes the shape of this layer.** See
`research/layer-b/` for the experiments.

The transport is not missing. Stock GTK4 still exports a menubar over
`org.gtk.Menus` and sets `_GTK_MENUBAR_OBJECT_PATH` on the window, and the
Unity panel already renders it - demonstrated with a twenty-line GTK4
application whose only unusual act is calling `gtk_application_set_menubar()`.
No patched package was involved.

Two things are actually in the way.

**There is no way to inject code into GTK4 applications.** GTK4 has no module
loading mechanism: `GTK_MODULES`, `gtk_module_init` and `gtk-modules` are all
absent from `libgtk-4.so.1` while present in `libgtk-3.so.0`. The way
`appmenu-gtk-module` reaches GTK3 applications - loaded into every process and
overwriting `realize` in the class vtable - has no GTK4 equivalent. Extending
that module to GTK4, which is what this section used to assume, is not
possible.

**The menubar must be set before window realize.** Attaching one afterwards
leaves the X11 property unset and the panel blank, with no error.

So the work is: get into the process before realize, which means `LD_PRELOAD`
symbol interposition (`libgtk-nocsd.so.0` already does this in the Unity
session), read the header bar's menu model through the public
`gtk_menu_button_get_menu_model()`, and set it as the menubar in time. If
applications turn out not to have populated their menu button that early, the
fix has to move into GTK4 itself.

This remains the most valuable and longest-lived work in the project: both the
X11 Unity and any future Wayland Unity need it.

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
