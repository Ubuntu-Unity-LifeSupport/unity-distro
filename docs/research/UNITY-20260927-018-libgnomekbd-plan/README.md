# UNITY-20260927-018: a plan for libgnomekbd leaving the archive (LP #2136945)

Documentation task: research and a recommendation, no code change; the
decision is the coordinator's and May's. Agent A, 2026-09-28. Earlier
assessment: `research/ucc-panels/` ("libgnomekbd (LP #2136945) - assessment
only", 2026-09-26). Archive, Debian, upstream and schedule facts come from a
delegated sweep on 2026-09-28 (~17:15Z); the usage in our packages from our
own source read.

## Summary

- **Ubuntu Unity 26.04 is not affected, for its whole life.** libgnomekbd
  3.28.1-3build1 is published in resolute and a released series never loses
  a package; resolute's standard support runs to 2031-05-29.
- **Nothing has been decided in Ubuntu.** LP #2136945 asks unity-control-center
  to *stop using* libgnomekbd; there is no removal request. Debian removed it
  on 2026-08-13 (RM #1144251), upstream is archived, and in 26.10 Unity is its
  only user, so an Ubuntu removal becomes likely once Unity stops depending on
  it, or at an archive clean-up that accepts breaking Unity.
- **The earliest series where it can go is 27.04** (development opens about
  2026-10-22, Feature Freeze 2027-02-25, release 2027-04-22). 26.10 releases
  on 2026-10-15 with it.
- **Our exit is small**: no package of ours calls the libgnomekbd API. We use
  two GSettings schemas and the `gkbd-keyboard-display` program, plus three
  build-dependencies of which two are unused and one only links.
- **Recommendation**: nothing to do for 26.04; drop the unused build
  dependencies whenever those packages are uploaded for another reason; and,
  only if we build for a series after 26.10, do option B (our own schema keys
  with a migration, `tecla` for "show layout") before that series' Feature
  Freeze. Track it with an alert, not by memory.

## What our packages use (FACT, source read 2026-09-28)

| Package (our branch) | Build | Runtime |
|---|---|---|
| unity-control-center (`ef8324f`, +unity2) | Build-Depends `libgnomekbd-dev`, not referenced by configure.ac - unused | Depends `gkbd-capplet (>= 3.5.90)`; region panel: `g_settings_new ("org.gnome.libgnomekbd.desktop")` unguarded (panels/region/gnome-region-panel-input.c:1810), keys `group-per-window`, `default-group`; "show layout" spawns `gkbd-keyboard-display -l "layout<TAB>variant"` (:1331-1337) |
| indicator-keyboard (`10eb95c`, +unity3) | Build-Depends `libgnomekbd-dev`; configure.ac `PKG_CHECK_MODULES([LIBGNOMEKBD], [libgnomekbdui])`, linked and `--pkg Gkbd-3.0` in lib/Makefile.am, but no `Gkbd.`/`gkbd_` call in lib/ | Depends `libgnomekbd-common` (the schemas); `new Settings ("org.gnome.libgnomekbd.desktop")` at start (lib/main.vala:144, unguarded); `org.gnome.libgnomekbd.keyboard` `layouts` read when converting old settings (:460); "show layout" spawns `gkbd-keyboard-display` (:1176-1180); tests use both schemas |
| unity-settings-daemon (`216f054`, +unity5) | Build-Depends `libgnomekbd-dev (>= 3.5.1)`, not referenced by configure.ac - unused | keyboard plugin: converting old libgnomekbd layouts/options, guarded by `schema_is_installed` (plugins/keyboard/gsd-keyboard-manager.c:2021-2089); Fcitx path `g_settings_new ("org.gnome.libgnomekbd.desktop")` unguarded (:1607), built (`--enable-fcitx`), reached when Fcitx 4's config description is found |

## What breaks, and how, if it leaves a series we build for

INFERENCE from the code (not run; GLib aborts a process that asks
`g_settings_new` for a schema that is not installed):

| Missing | Effect |
|---|---|
| `libgnomekbd-common` (schemas) | indicator-keyboard: uninstallable (Depends), and if forced, aborts at start - no keyboard indicator. u-c-c: aborts when the "Ввод текста" (region) panel opens. u-s-d: aborts in the Fcitx path (Fcitx 4 users only). |
| `gkbd-capplet` (`gkbd-keyboard-display`) | u-c-c: uninstallable (Depends). "Show keyboard layout" in u-c-c and in the indicator menu: spawn fails with a warning, nothing shown. |
| `libgnomekbd-dev` | u-c-c, u-s-d, indicator-keyboard fail to build (Build-Depends; the first two do not use it, indicator-keyboard only links `libgnomekbdui`). |

On upgrade to such a series, the old packages would stay installed from the
previous release until something removed them; new installs could not get
u-c-c or indicator-keyboard at all.

## Who else uses it (FACT, sweep, amd64 main+universe)

- resolute: Build-Depends `libgnomekbd-dev` - u-c-c, u-s-d, indicator-keyboard,
  cinnamon-control-center, cinnamon-settings-daemon, xapp, gnome-screensaver;
  binaries - u-c-c (gkbd-capplet), indicator-keyboard (libgnomekbd-common),
  cinnamon, cinnamon-screensaver, cinnamon-control-center,
  cinnamon-settings-daemon, libxapp1; budgie-control-center Recommends and
  ayatana-indicator-keyboard Suggests gkbd-capplet.
- 26.10 (stonking): **only Unity** - u-c-c 0ubuntu16, u-s-d, indicator-keyboard
  0ubuntu4. Cinnamon 6.6, xapp 3.2.2-2, budgie-control-center 2.1.3-1,
  ayatana-indicator-keyboard 26.6.2 and gnome-screensaver no longer use it.
- What the others did: GNOME replaced gkbd-keyboard-display with `tecla`
  (gnome-control-center Depends tecla, in main); MATE uses its fork libmatekbd
  and `matekbd-keyboard-display`; Cinnamon 6.6 rewrote keyboard handling (also
  for Wayland); ayatana-indicator-keyboard never linked libgnomekbd (libxklavier,
  libxkbregistry) and runs `matekbd-keyboard-display` on MATE, `tecla <layout>`
  on Lomiri, otherwise still `gkbd-keyboard-display` (upstream source; Debian
  24.7.2-7 made `matekbd-keyboard-display | tecla` a Depends).
- Related Ubuntu bugs, all by the Ubuntu Desktop team's Jeremy Bícha:
  LP #2136945 "Stop using libgnomekbd" (u-c-c, 2025-12-21, New/High, no
  comments); LP #2136946 "Switch from indicator-keyboard to
  ayatana-indicator-keyboard?" (lowered to Low on 2026-02-27: "does not appear
  to have the necessary features for integration with Unity"); LP #2163390
  "indicator-keyboard depends on unmaintained libgnomekbd" (2026-08-13,
  New/High, tagged for 26.10).

## Options

Estimates are working time for one agent, builds and a VM check included.

| | Option | Work | For | Against |
|---|---|---|---|---|
| A | Keep depending; if it leaves a series we build for, carry libgnomekbd 3.28.1 in our aptly | ~2 h per series (rebuild the last Ubuntu source) | no code change | we would carry an archived, X11-only library nobody maintains; it only postpones B |
| **B** | **Stop depending**: (1) the two keys we write/read move to schema IDs of our own (e.g. in indicator-keyboard's or unity-schemas' namespace) with a one-time migration from `org.gnome.libgnomekbd.*` where installed - u-s-d already has this pattern (`schema_is_installed` + convert); (2) drop the three build dependencies (u-c-c, u-s-d: delete from debian/control; indicator-keyboard: remove the `libgnomekbdui` check and `--pkg Gkbd-3.0`); (3) "show layout" runs `tecla <layout>` (or `layout+variant`, syntax to be checked), falling back to `matekbd-keyboard-display`, then `gkbd-keyboard-display`, and hides the item when none is installed; Depends -> `tecla | gkbd-capplet` | ~1.5-2.5 days (three packages, tests, a Unity/X11 run of tecla on the VM) | what GNOME, MATE and Cinnamon did; removes the problem instead of carrying it; each part testable on resolute now | touches three packages; tecla is GTK 4 + libadwaita (heavier, not yet run under Unity) |
| B' | Only the cheap parts of B now: (2) the unused build-deps, and guarding the three unguarded `g_settings_new` with a schema lookup so a missing schema degrades instead of aborting | ~0.5 day | no user-visible change on resolute; makes a later B smaller | on its own it does not make the packages installable without libgnomekbd |
| C | Replace indicator-keyboard with ayatana-indicator-keyboard | several days + unknowns | maintained | the Ubuntu Desktop team judged it lacks what Unity needs (LP #2136946); it would also need a new "show layout" and u-c-c still needs B; not measured by us |
| D | Own keyboard layout dialog | days | no new dependency | reimplements what tecla already does |

None of these needs an upstream change. The B patch could later be offered
for LP #2136945; that is an outward action and needs May.

## Recommendation

1. **26.04 (what we ship): do nothing now.** Nothing breaks.
2. **Whenever u-c-c, u-s-d or indicator-keyboard is uploaded for another
   reason: include B' (2)** - dropping the unused build dependencies; no
   version for this alone.
3. **If and when we decide to build for a series after 26.10: do B** before
   that series' Feature Freeze - for 27.04 that is **2027-02-25**; start no
   later than mid-January 2027. Whether we build beyond 26.04 at all is the
   decision this plan depends on (C/May).
4. **Tracking**: an alert, the way `xorg-watch` does it
   (UNITY-20260927-013): a small watcher that raises when libgnomekbd is no
   longer published in the current development series, or when LP #2136945 /
   #2163390 change status - proposed as a separate tool task. Subscribing to
   the Launchpad bugs is an action under May's account and is his call.

## Timeline (FACT, Ubuntu release schedules)

- 26.10 "Stonking Stingray": Beta 2026-09-24, Final Freeze 2026-10-08,
  release 2026-10-15 - with libgnomekbd (no removal record, nothing in
  -proposed).
- 27.04 (codename not yet announced; "27.04" in the task is this release,
  not a date): opens about 2026-10-22, Debian Import Freeze and Feature
  Freeze 2027-02-25, UI Freeze 2027-03-18, Beta 2027-04-01, Final Freeze
  2027-04-15, release 2027-04-22.

## Gaps

- The "what breaks" table is from the code, not run; a VM run with
  `libgnomekbd-common` and `gkbd-capplet` removed would confirm it.
- tecla's command-line syntax for a variant and its behaviour under
  Unity/X11 are not checked.
- ayatana-indicator-keyboard's fitness for Unity is the Ubuntu Desktop team's
  judgement, not measured here.
- Ubuntu archive-admin tooling (a "kept for Unity" note, a sync blocklist)
  not checked; upstream's exact archive date not pinned (between 2024-08 and
  2025-12).

## Sources

LP [#2136945](https://bugs.launchpad.net/bugs/2136945),
[#2136946](https://bugs.launchpad.net/bugs/2136946),
[#2163390](https://bugs.launchpad.net/bugs/2163390); Debian
[RM #1144251](https://bugs.debian.org/1144251),
[tracker](https://tracker.debian.org/pkg/libgnomekbd); upstream
[gitlab.gnome.org/Archive/libgnomekbd](https://gitlab.gnome.org/Archive/libgnomekbd);
[Linux Mint 22.3 notes](https://www.linuxmint.com/rel_zena_whatsnew.php);
Ubuntu schedules [26.10](https://documentation.ubuntu.com/release-notes/26.10/schedule/),
[27.04](https://documentation.ubuntu.com/release-notes/27.04/schedule/).
