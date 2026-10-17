# unity-gtk4-menu: the GTK4 global menu is lost when the session's own LD_PRELOAD is not empty (UNITY-20260927-039)

Owner: agent B (target2).

```yaml
task: UNITY-20260927-039
title: no Xsession snippet; the GTK4 global menu is lost when the session's LD_PRELOAD is non-empty
package: unity-gtk4-menu (0.13 live)
target_series: resolute
status: reproduces on the current stack (2026-10-17); fix to be designed (Design Challenger), proposed for 0.14
```

## Background

UNITY-20260927-022 found the mechanism on 2026-09-27, with gtk-nocsd +unity3 and unity-gtk4-menu 0.9 (bare names):
1. `~/.xsessionrc` exports an LD_PRELOAD of the user's own.
2. 51gtk-nocsd adds gtk-nocsd to it.
3. `95dbus_update-activation-env --all` exports the X session's LD_PRELOAD to the systemd user manager, replacing the
   value the user manager built from environment.d.

unity-gtk4-menu, which only sets environment.d, is lost. -022 concluded that unity-gtk4-menu owns its own entry and
must add it in Xsession too (the 90atk-adaptor precedent). gtk-nocsd's script owns only gtk-nocsd.

Since then May's 12.10 decision moved both libraries to preloading by path (`/usr/$LIB/...`). gtk-nocsd +unity4
rewrote 51gtk-nocsd so that it starts from the user manager's value. This task checks whether that already covers the
case.

## Measured (2026-10-17, target2; `probe.sh`)

target2: Clean-2 → live (InRelease 2026-10-17 06:06:43 UTC), with libgtk-nocsd0 4.8-1+unity5, libunity-gtk4-menu0 0.13,
unity-session 49.4+unity2, dbus-x11 and dbus-user-session 1.16.2-2ubuntu4, and gnome-calculator (GTK 4) as the
application. Each run is a cold Unity session (autologin).

| run | ~/.xsessionrc | user manager's LD_PRELOAD (compiz, panel service and hud-service the same) | gnome-calculator, started through the user manager |
|---|---|---|---|
| control (logs/01) | none | `/usr/$LIB/libunity-gtk4-menu.so.0:/usr/$LIB/libgtk-nocsd.so.0` | maps both libraries; exports `/org/gnome/Calculator/menus/menubar` |
| the -022 case (logs/03) | `export LD_PRELOAD=libm.so.6` | `/usr/$LIB/libgtk-nocsd.so.0:libm.so.6` | maps gtk-nocsd only; **no menubar exported** |

**It still reproduces.** 51gtk-nocsd starts from the user manager's value only when the session's own LD_PRELOAD is
empty (`if [ -z "${LD_PRELOAD-}" ] ...`). When `~/.xsessionrc` has set one, the script prepends gtk-nocsd to it. 95dbus
then exports that list over environment.d's value, so unity-gtk4-menu's entry is gone from the user manager and from
everything the session starts.

## Direction (to be designed for the Design Challenger)

As -022 concluded, unity-gtk4-menu adds its own entry in Xsession: a snippet `/etc/X11/Xsession.d/5Xunity-gtk4-menu`
of its package, after 51gtk-nocsd and before 95dbus. It would do for `/usr/$LIB/libunity-gtk4-menu.so.0` what
51gtk-nocsd does for gtk-nocsd:
- add the path once, in any form;
- skip it when the user or administrator has turned it off with an `environment.d/60-unity-gtk4-menu.conf` of their
  own;
- keep the order the user manager uses without a session LD_PRELOAD (unity-gtk4-menu first);
- pass it to STARTUP, as 51gtk-nocsd does for ssh-agent.

The alternative is to change 51gtk-nocsd so that it also merges the user manager's value when the session has its own.
That is gtk-nocsd's script and gtk-nocsd's own scope (-022), so it is weighed and not taken.
