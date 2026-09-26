# Rebuilds that silently lose files (systemd.pc moved to systemd-dev)

Agent B, 2026-09-26, coordinator's task B-7. `systemd.pc` moved to
`systemd-dev`. A source whose Build-Depends does not name it gets an empty
`systemduserunitdir` on a rebuild, and its user units or targets vanish:
- indicator-bluetooth and -printers lost them (`research/indicator-units/`);
- libindicator refused to build (`research/rebuild-trial/`).

This survey looks for more.

## Method

1. **Candidates.** Take the recursive dependencies of `ubuntu-unity-desktop`
   in resolute and keep the Unity/Canonical-era stack that is rarely
   rebuilt: 35 sources. Actively rebuilt Debian packages were left out
   (ayatana-*, gcc, linux and the like). So were the sources we already
   carry.
2. **Risky files.** Download their archive binaries. 21 sources ship at
   least one file under `systemd/{user,system}/`, `dbus-1/services/`,
   `xdg/autostart/` or `glib-2.0/schemas/`; only those can lose one.
3. **Compare.** Rebuild those 21 in a clean `sbuild -d resolute`, archive
   only. `compare.py` compares every binary package's file list with the
   archive's, ignoring doc and `.build-id`.

## Result

| source | rebuild | lost files | action |
|---|---|---|---|
| a11y-profile-manager, appmenu-registrar, bamf, gsettings-ubuntu-touch-schemas, notify-osd, onboard, unity-indicator-appearance, unity-tweak-tool, vala-panel-appmenu, zeitgeist | builds | none | - |
| indicator-application, indicator-appmenu, indicator-notifications, unity-lens-applications, unity-lens-files, unity-scope-home | builds (rebuild-trial) | none | - |
| **indicator-messages** 0ubuntu7 | FTBFS: `missing files: usr/lib/systemd` | the user unit (the systemd.pc trap) | **fixed in 26.10**: 0ubuntu8 (systemd-dev, LP #2166912). It builds in resolute, and nothing is lost. Carrying it is proposed; nobody owns the package |
| **hud** | FTBFS in three layers: CMake 4 (min < 3.5); empty `SYSTEMD_USER_DIR` (the trap, here as a hard error for `hud.service` and `window-stack-bridge.service`); tests need C++17 for googletest | - | two layers fixed in `+unity1` WIP (`package-patches-b/debdiff/`); the third is still open. Nobody owns it |
| **session-migration** | FTBFS: CMake 4; then a test regex that breaks on a `+` in the build path (any `+unityN` version) | none after the fix | `+unity1` built, 9 of 9 tests; not in aptly; nobody owns it |
| **unity-greeter** | unsatisfiable: `liblightdm-gobject-1-dev` was split (lightdm-vala), as for indicator-keyboard | - | not built; nobody owns it |
| **overlay-scrollbar** | FTBFS: needs Ubuntu's old GTK patch (`ubuntu_gtk_*_use_overlay_scrollbar`) | - | dead. 26.10 has only a no-change rebuild in -proposed, deleted from resolute. List only |

Apart from the systemd trap, none of the builds that succeeded lost a file.
Two sources carry it: indicator-messages (26.10 already fixed it) and hud.

## libindicator +unity1: published

The six binaries against the archive's:
- file lists are equal (only the changelog is a file instead of a symlink
  in -dev and -tools);
- the exported symbols are equal (34 and 40);
- shlibs and symbols files are equal;
- `indicator-common` including `indicators-pre.target` is identical;
- Depends differ only by the t64 names.

The binaries change nothing, but the source in aptly now builds and keeps
the target that `unity-panel-service` binds to.

Files: `compare.py`; the rebuild logs are in `~/work/b/b7` and
`~/work/b/b7fix` on builder.
