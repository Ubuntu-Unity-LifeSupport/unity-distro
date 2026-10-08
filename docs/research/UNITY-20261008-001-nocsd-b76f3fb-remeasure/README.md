# UNITY-20261008-001: the global-menu figures on GTK-NoCSD main b76f3fb

Owner: agent B (target2). The GTK-NoCSD main on codeberg
(MorsMortium/GTK-NoCSD) now carries our five global-menu patches,
`3b1d4a3..2d50fe9` (authored by NeiroNext, the same changes as our series
`8857fce..60ec176` on `a57e976`), followed by ten commits of the author,
`092e184..b76f3fb` (2026-10-06..07). This card measures both, with the same
scripts, on the same system, on the same day.

## What changed between the two (from the source)

- **The switch.** Our series: `GTK_NOCSD_GLOBAL_MENU=1` (2 mentions in
  2d50fe9). b76f3fb: `GTK_NOCSD_MENU=1` (`GET_VARIABLE(GTKNoCSDMenu,
  GTK_NOCSD_MENU)`, GTK-NoCSD.c:513); `GTK_NOCSD_GLOBAL_MENU` no longer
  appears.
- **Grouping.** b76f3fb adds `GTK_NOCSD_MENU_GROUP` (GTK-NoCSD.c:514-517,
  `GTKNoCSDMenuGrouping` :4010): `1` always groups the items under one
  holder, `2` never does, unset groups only when the menu has entries
  without submenus (README).
- **The shell setting.** Our series exported only while
  `gtk-shell-shows-menubar` is true (4 mentions in 2d50fe9); b76f3fb has no
  mention of it.
- **GTK3.** 092e184 "Cleanup, initial GTK3 support for global menus",
  09b879f "Support 2 GTK3 methods to create menus". The realize hook stays
  GTK4-only (`GTKNoCSDMenuHook`: `GTKNoCSDGTKVersion == 4`, :4338).
- **Others:** 5611d39 "Prefer menu buttons in header", 1ddcf1f "Strip label
  formatting tags", 90f928c / 928e18c (first window added to the
  application), b76f3fb "Disallow buttons with a label inside them, which
  is not in a popover".

## Where it ran

target2, checked from inside on 2026-10-08 (no VirtualBox control: the
vbox server was not reachable, so no rollback):

- Clean-2 + our repository by a user's `full-upgrade` on 2026-10-02
  (gtk-nocsd `4.8-1+unity3`, hud `+unity3`, ...), plus the leftovers of
  UNITY-20260929-002: scripts in `~/b029`, the package `xdotool`.
- The Unity session: `LD_PRELOAD=libgtk-nocsd.so.0` (the package's),
  `GTK_MODULES=appmenu-gtk-module:gail:atk-bridge`, no
  `libunity-gtk4-menu`; `/etc/environment.d` and `Xsession.d` as the
  packages install them.
- The guest clock was 5 days behind (2026-10-03T02:07Z against builder
  2026-10-08T02:30Z) while `timedatectl` reported "System clock
  synchronized: yes" and systemd-timesyncd was inactive (chrony is the
  active service). `timedatectl set-ntp false; set-ntp true` brought it to
  builder time within 20 s (UNITY-20260929-022).
- unattended-upgrades then upgraded archive packages (LibreOffice, poppler,
  freetype, libpng, freerdp, ...), before the measurements.
- Installed for this task from the archive, as in UNITY-20260927-034: the
  44 audited applications, `git`, `libadwaita-1-dev`, `libgtk-4-dev`,
  `libgtk-3-dev`, `gdb`.
- Builds on target2 with the projects' Makefile, gcc 15.2.0: our series
  `60ec176` (0 warnings) and `b76f3fb` (0 warnings).
- The scripts are those of research/nocsd-gaps (`variant.sh`, `audit.py`)
  and `nocsd-desktops/breadth-any.sh`, unchanged; `run081.sh` (here) runs
  the variants, kills leftover audited applications before each one, and
  puts the packaged library back at the end. `count.py` is the one of
  UNITY-20260927-034.

## Results (2026-10-08, 03:07-04:40Z)

S = our series on a57e976 (`60ec176`), U = b76f3fb. 43 audited
applications (the 44 minus Apostrophe, which opens no window), as in
UNITY-20260927-034. Files in `logs/`.

| measurement | S (`a57e976` + our series) | U (`b76f3fb`) |
|---|---|---|
| switch | `GTK_NOCSD_GLOBAL_MENU=1` | `GTK_NOCSD_MENU=1` |
| variable off: apps exporting | 0 of 43 (`var-S-off`) | 0 of 43 (`var-U-off`) |
| U with the old variable `GTK_NOCSD_GLOBAL_MENU=1` | - | 0 of 43 (`var-U-oldvar`) |
| menus found, full run | 40 of 43 (`var-S-on`) | 39 of 43 (`var-U-on`) |
| menus found, debug run | 41 of 43 (`var-S-dbg`) | 41 of 43 (`var-U-dbg`) |
| apps without a menu, full run | gnome-contacts, gnome-tour, showtime | gnome-contacts, gnome-tour, showtime, gnome-calendar |
| the same, debug run | gnome-contacts, gnome-tour | gnome-contacts, gnome-tour |
| gnome-calendar and showtime, 5 separate starts each (`rep-*`) | 5/5 and 5/5 | 5/5 and 5/5 (also 5/5, 5/5 with `GROUP=2`) |
| items that cannot be activated (MISSING) | 3: Déjà Dup select-all, Epiphany uninstall-web-app, Sudoku reset-board | the same 3 |
| shape, default | one holder entry in 40 of 40 | one holder entry in 39 of 39 |
| `GTK_NOCSD_MENU_GROUP=1` | - | holder in 39 of 39 (`var-U-g1`, same as default) |
| `GTK_NOCSD_MENU_GROUP=2` | - | flat in 40 of 40: the items as top-level entries, 2 to 18 per app (`var-U-g2`, `shapes.txt`) |
| labels with a mnemonic underscore (`_Сохранить`) | 229 | 0 |
| hidden button: items dropped as custom widgets (debug build) | 7 apps: dialect 2, gnome-calendar 2, gnome-sudoku 6, gnome-text-editor 6, kgx 4, loupe 4, yelp 2 | the same 7 apps, the same counts |
| Nautilus Undo after a rename | "_Отменить переименование" | "Отменить переименование" |
| Papers, start page | its own menu: Shortcuts, Help, About | the same |
| Papers, started with a PDF | the document menu (Print, Fullscreen, Presentation, ...) | the same items |
| Console (kgx) | its own menu: New Window, Show All Tabs, Fullscreen, Preferences, Shortcuts, About | the same 6 items |
| Pinta 3.1.2, 3 starts | its menubar, 6 top menus (File, Edit, Layers, Add-ins, Window, Help), 39 items, 0 MISSING, 3/3 | the same, 3/3; with `GROUP=2` the same 6 top menus |
| GTK3, 10 apps with a menu button | 0 of 10 export a menu (`g3-S-on`) | 9 of 10 (`g3-U-on`); variable off 0 of 10; nothing for gnome-taquin (see the notes) |
| GTK3 shape | - | default: one holder in 9 of 9; `GROUP=2`: flat, 3 to 7 entries |
| the types bug (`typesorder`, gdb) | reproduces: with the early GObject `GTKNoCSDGTKWindow=0` at exit; control fetches the type | reproduces, the same counts (`typesorder.txt`) |

Notes on the table:

- **Full run against debug run.** The two full runs and the debug runs use
  the same applications in the same order. gnome-calendar ("NO-GTK-PROPS"
  in U-on and U-g1) and showtime (the audit's D-Bus call timed out, as in
  UNITY-20260927-034) exported their menus in every separate start, for
  both builds. INFERENCE: the misses come from slow starts in the long
  run, not from a build.
- **Underscores.** U passes each label through
  `pango_parse_markup(label, -1, '_', ...)` (GTK-NoCSD.c:3933, 1ddcf1f
  "Strip label formatting tags"); with `'_'` as the accelerator marker the
  mnemonic underscores are removed with the tags. Whether the Unity panel
  then offers Alt mnemonics in these menus was not tested.
- **GTK3 apps:** gnome-disks, gnome-connections, dconf-editor and seahorse
  (libhandy), gnome-taquin, gnome-tetravex, four-in-a-row, five-or-more,
  hitori, gnome-klotski. Their session also loads `appmenu-gtk-module`
  through `GTK_MODULES`; the audit reads only the `_GTK_*` properties and
  the `org.gtk.Menus` export. The 9 apps U exports for use their own menu
  path (e.g. gnome-tetravex `/org/gnome/Tetravex/menus/menubar`, 24 items).
  For gnome-taquin U exports nothing; the window's
  `_GTK_MENUBAR_OBJECT_PATH` is `/org/appmenu/gtk/window/0`, which belongs
  to appmenu-gtk-module, and `org.gtk.Menus Start` on it returns no items.
  Under S all 10 windows carry that same empty appmenu-gtk-module menubar
  (found by the Verifier).

## Crash reports during the runs

The runs left crash reports for showtime and Apostrophe (six apport
dialogs on the display afterwards). Both are Python exceptions caught by
apport's hook, not core dumps, and apport keeps one report per executable
and overwrites it, so the files alone do not say which run produced them.
`crash081.sh` (`logs/crashes.txt`) starts each app as the audit does
(session environment, `audit.py` after 7 s, then SIGTERM) and looks for a
traceback in the app's own stderr:

| condition | showtime: traceback | Apostrophe: traceback |
|---|---|---|
| no preload (`LD_PRELOAD` empty) | 0/3, then 2/5 | 2/3 |
| the packaged library (4.8-1+unity3) | 0/3, then 5/5 | 2/3 |
| S, variable off | 2/5 | - |
| S, `GTK_NOCSD_GLOBAL_MENU=1` | 3/3, then 5/5 | 2/3 |
| U, variable off | 1/3, then 4/5 | 3/3 |
| U, `GTK_NOCSD_MENU=1` | 3/3, then 5/5 | 2/3 |

- showtime: `TypeError: Argument 0 does not allow None as a value` in
  `showtime/mpris.py:209` (`_on_method_call`, building the reply variant
  of an MPRIS call), as in UNITY-20260927-034.
- Apostrophe: `TypeError: cannot pickle 'ApostropheTextView' object` (its
  own `multiprocessing` use).
- Both occur without any preload, so they are the applications' own
  errors; neither build causes them, and S and U show them alike. How
  often showtime hits it varies between runs (0/3 and 2/5 without a
  preload).

target2 after the runs: the packaged `libgtk-nocsd.so.0` is back
(`dpkg -V libgtk-nocsd0` clean); the applications, dev packages, gdb,
dotnet-sdk-10.0 and the Pinta build stay installed; not rolled back
(no VirtualBox control). The audit's `pkill -x` did not catch Fragments
(it runs as `ld-linux-x86-64`, the library started as the loader), so one
Fragments with its `transmission-daemon` per variant and Apostrophe's
`multiprocessing` helpers were left running; they were killed by PID
afterwards. The system `transmission-daemon` service (installed with
Fragments) keeps running.

## Verification: PASS (REVIEWED)

An independent Verifier re-measured four figures on target2 (04:39-04:52Z):

1. U with only `GTK_NOCSD_GLOBAL_MENU=1`: 0 of 43 (the full audit); the
   positive control with `GTK_NOCSD_MENU=1` exported menus for Text Editor,
   Nautilus and Calculator.
2. GTK3: U 9 of 10, S 0 of 10; gnome-taquin as in the notes above.
3. Mnemonic underscores on three apps: S 27 labels, U 0; explained by the
   `pango_parse_markup(..., '_', ...)` call at GTK-NoCSD.c:3927-3938.
4. typesorder on U: early `GTKNoCSDGTKWindow=0`, control the GtkWindow
   type, as in `logs/typesorder.txt` (the breakpoint hit counts differ by a
   few calls, the values at exit match).

Remarks, applied: the gnome-taquin wording (U exports nothing; the empty
menubar is appmenu-gtk-module's); the leftover processes above. The crash
attribution was added after the round, at the coordinator's request.

## Alt mnemonics on the Unity panel: not tested

Tried with `mnemo081.sh` (`logs/mnemonics.txt`), in the 10-15 minutes
given, on Pinta (Alt+F, its top menu is `_File` in S and `File` in U) and
GNOME Text Editor (F10, then the item mnemonic). In both builds the keys
sent with `xdotool` did not open a panel menu: no new window appeared, and
in Text Editor the letter was typed into the document. The screenshots
(`gnome-screenshot`) were black or showed another window, and the vbox
screenshot was not available. Afterwards the visible windows on the
display were a light-locker window and six apport "Отчёт о неполадке"
dialogs (for the crashes listed above), so the keys did not go to the
panel. So the method did not reach the panel, and
whether Alt mnemonics work with S or with U is **not tested**. A test needs
real keyboard input on the panel (vbox `send_keys` and `screenshot`).

## Verification of the crash section: PASS (REVIEWED)

A second independent Verifier started the apps itself, without
crash081.sh:

- With `LD_PRELOAD` empty (libgtk-nocsd absent from `/proc/PID/maps` in
  all 8 runs): showtime 4 of 5 runs with the `TypeError` traceback,
  Apostrophe 2 of 3 with the pickling `TypeError`.
- showtime with the session's packaged library: 0 of 5.
- In `showtime/mpris.py` the `None` is the return of `_get(iface, prop)`,
  the `org.freedesktop.DBus.Properties.Get` handler, for an interface
  showtime does not serve (`_get_all` gives `{}` or `None`); line 209 then
  builds a `(v)` reply from `(None,)`. Which session client sends that
  `Get` was not identified.

The rates per condition vary between runs and are not a measure of any
build; the finding is that both errors occur without a preload.
