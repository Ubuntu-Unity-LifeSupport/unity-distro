# The gtk-nocsd global menu under Xfce and KDE Plasma

Agent B, 2026-09-25, on `target2`, with May's approval; target2 rolled back to
`Clean-2` afterwards. Tests the patch of `research/nocsd-upstream/`
(`libgtk-nocsd0 4.8+git20260924.6b1f70a-1+unity2~menu5`) outside Unity, in
real sessions rather than under Xvfb with a fake flag.

Installed from the 26.04 archive (`--no-install-recommends`): Xfce 4.20
(`xfce4-session`, `xfwm4`, `xfce4-panel`, `xfdesktop4`, `xfce4-settings`) with
`xfce4-appmenu-plugin` and `appmenu-registrar` (vala-panel-appmenu 25.04);
Plasma 6.6.4 X11 (`plasma-desktop`, `plasma-session-x11`, `kwin-x11`, then
`kde-config-gtk-style`). LightDM stayed the display manager; the session was
switched with `autologin-session=` (`xfce`, `plasmax11`).

## Results

| | Xfce 4.20 | Plasma 6.6.4 (X11) |
|---|---|---|
| Sets `gtk-shell-shows-menubar` by itself | no | no |
| Needed by hand | `xfconf-query -c xsettings -p /Gtk/ShellShowsMenubar -n -t bool -s true`; AppMenu plugin on the panel | `gtk-shell-shows-menubar=true` in `~/.config/gtk-4.0/settings.ini`; Global Menu widget on the panel |
| LD_PRELOAD reaches applications | **no** with Debian's `environment.d` alone (see below); yes with `export LD_PRELOAD=libgtk-nocsd.so.0` in `~/.xsessionrc` | yes (Plasma starts through systemd, `environment.d` applies) |
| 18 applications (`breadth-xfce.txt`, `breadth-kde.txt`) | 18/18 exported, per-item audit identical to Unity | 18/18, identical to Unity |
| classtest stand-ins | follow the enabled state, activate once | same |
| Menu shown on the panel | yes (`xfce-chars-menu.png`), "About" from the panel opens About | yes, through gmenudbusmenuproxy (`_KDE_NET_WM_APPMENU_*` set on the window; `kde-chars-menu.png`), "About" opens About |
| Without the flag | nothing exported, window unchanged | nothing exported (checked with an empty config) |
| gtk-nocsd's own job | xfwm4 title bar | KWin title bar |
| Crash reports, kernel segfaults | none | none |

## What this means

**The code works on both desktops.** Once the flag is on, the exported menu
is the same as under Unity for all 18 applications, and both panels show and
activate it.

**Out of the box it does not.** Neither desktop sets
`gtk-shell-shows-menubar`:

- Xfce: it has to be set through xfconf. Whether vala-panel-appmenu's setup
  guides tell Xfce users to set it was not checked; the plugin itself does
  not set it (the property did not exist after installing it).
- Plasma: nothing in Plasma sets it. `kde-config-gtk-style`'s `gtkconfig.so`
  contains no menubar setting at all; the Global Menu widget registers the
  appmenu registrar, which gmenudbusmenuproxy waits for, but GTK is never
  told. A Plasma user would have to add the line to `settings.ini` by hand.

So the switch chosen for point 3 is off on Plasma unless configured.
**Correction 2026-09-25 (`research/nocsd-reply2/`):** the reason once given
for it - that GTK would otherwise draw a duplicate menubar in the window -
does not hold for GTK4, whose `show-menubar` defaults to FALSE. An
alternative would be to also enable export when `com.canonical.AppMenu.
Registrar` is on the session bus - what appmenu-gtk-module uses for GTK3 - and
then hide the application window's own menubar (`show-menubar` FALSE) so
GTK does not draw it in the window. Not built; a design question for the
patch, and for the maintainer if it is offered.

**Xfce and Debian's gtk-nocsd.** Under Xfce, `xfce4-session`, `xfce4-panel`
and `xfdesktop` are started from Xsession and do not see `environment.d`,
so neither do the applications they launch: gtk-nocsd is not loaded at all -
decorations included - unless `LD_PRELOAD` is exported in the X session
(upstream's README suggests a shell profile). That is a packaging matter of
gtk-nocsd on Xfce, independent of the menu; recorded, not reported.

## Not tested

MATE and Budgie (same vala-panel-appmenu as Xfce); Wayland (no desktop reads
GTK's menu there); a full Kubuntu/Xubuntu install with recommends.

Files: `breadth-any.sh` (breadth run taking the environment of any session
process, `SESSPROC=xfce4-session|plasmashell`), `xfce-plugin.sh` (adds the
AppMenu plugin through xfconf; `xfce4-panel --add` opens an interactive
dialog instead).
