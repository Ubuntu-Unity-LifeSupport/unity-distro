# UNITY-20260927-018: a plan for libgnomekbd leaving the archive (LP #2136945) - DRAFT

Work in progress, paused for UNITY-20260927-009. Documentation task: research
and a recommendation, no code change. Earlier assessment:
`research/ucc-panels/` ("libgnomekbd (LP #2136945) - assessment only",
2026-09-26).

## What our packages use (FACT, source read 2026-09-28)

No package of ours calls the libgnomekbd API. What is used:

| Package (our branch) | Build | Runtime |
|---|---|---|
| unity-control-center (`ef8324f`, +unity2) | Build-Depends `libgnomekbd-dev`, not referenced by configure.ac - unused | Depends `gkbd-capplet (>= 3.5.90)`; region panel: `g_settings_new ("org.gnome.libgnomekbd.desktop")` unguarded (gnome-region-panel-input.c:1810), keys `group-per-window`, `default-group`; "show layout" spawns `gkbd-keyboard-display -l "layout<TAB>variant"` (:1331-1337) |
| indicator-keyboard (`10eb95c`, +unity3) | Build-Depends `libgnomekbd-dev`; configure.ac `PKG_CHECK_MODULES([LIBGNOMEKBD], [libgnomekbdui])`, linked and `--pkg Gkbd-3.0` in lib/Makefile.am, but no `Gkbd.`/`gkbd_` call in lib/ | Depends `libgnomekbd-common` (the schemas); `new Settings ("org.gnome.libgnomekbd.desktop")` at start (lib/main.vala:144, unguarded); `org.gnome.libgnomekbd.keyboard` `layouts` read when converting old settings (:460); "show layout" spawns `gkbd-keyboard-display` (:1176-1180); tests use both schemas |
| unity-settings-daemon (`216f054`, +unity5) | Build-Depends `libgnomekbd-dev (>= 3.5.1)`, not referenced by configure.ac - unused | keyboard plugin: converting old libgnomekbd layouts/options, guarded by `schema_is_installed` (gsd-keyboard-manager.c:2021-2089); Fcitx path `g_settings_new ("org.gnome.libgnomekbd.desktop")` unguarded (:1607), built (`--enable-fcitx`), reached when Fcitx 4's config description is found |

GLib aborts the process when `g_settings_new` is given a schema that is not
installed, so without `libgnomekbd-common` (INFERENCE from the code; not run):
indicator-keyboard aborts at start; u-c-c aborts when the region panel
opens; u-s-d aborts in the Fcitx path. Without `gkbd-capplet`, "show layout"
fails to spawn (a warning, nothing shown).

Reverse dependencies in resolute (apt-cache rdepends on builder):
`libgnomekbd-common` <- indicator-keyboard, libgnomekbd8;
`gkbd-capplet` <- cinnamon, unity-control-center;
`libgnomekbd8` <- cinnamon-control-center, cinnamon-settings-daemon,
gir1.2-gkbd-3.0, gkbd-capplet, libgnomekbd-dev, libxapp1;
`gir1.2-gkbd-3.0` <- cinnamon, cinnamon-screensaver.

Available in resolute for a replacement: `tecla 49.0-2` (GNOME's keyboard
layout viewer, GTK 4 + libadwaita), `ayatana-indicator-keyboard 24.7.2-5build1`
(libxklavier, AccountsService, libxkbregistry).

## Pending

Archive/Debian/upstream state, LP #2136945 details, 26.10 reverse
dependencies, other desktops' choices and the 27.04 schedule: delegated sweep
running. Options with estimates and the recommendation follow.
