# UNITY-20260927-034: our global-menu series on GTK-NoCSD main a57e976

Owner: agent B (target2). Scope, as set by the coordinator on 2026-09-28:

- carry our five-commit global-menu series (research/nocsd-gaps) onto the
  current main of codeberg MorsMortium/GTK-NoCSD and record its hash;
- build every combination;
- re-measure the menu figures on the same 44 applications by the same
  scenarios;
- add the result to the findings of UNITY-20260927-038.

Out of scope: the dialog-title fix (upstream `af90f21` is our code) and the
types bug (re-checked in 038). Nothing was sent anywhere.

**Main:** `a57e976251b54f672a68ca7246c2e3c49a1d5168` ("Reset theme right
before GTK init", 2026-09-28 18:59 +0200).

## The port

The series is generated, not hand-edited. `research/nocsd-gaps/split/gen.py`
inserts the parts into upstream's `GTK-NoCSD.c` at small, unique anchors.
The anchors are the variables, the type list, the `LOAD_SYMBOL`/`GET_SYMBOL`
lists, the end of `GTKNoCSDGetReferences` and the `gtk_window_present`
hook. Our functions come from `funcs.json`, so none of upstream's
functions is overwritten.

- **The generator reproduces the committed series exactly.** On `6b1f70a`,
  generator + Uncrustify 0.78.1 (upstream's config) gives the five commits
  of `split/patches` with 0 differing lines (`logs/build-combinations.txt`).
- **Every anchor still matches on `a57e976`.** `git am` of the old patches
  failed only on context: upstream added `gtk_widget_add_css_class` and
  `gtk_settings_get_for_display` next to our `LOAD_SYMBOL` line.
- **None of upstream's changes since `6b1f70a` touches a menu line, or
  `gtk-shell-shows-menubar`.** `2cdf402` moved the settings setup into
  `GTKNoCSDDoSettings`, next to our parts, which is why the figures were
  measured again rather than carried over.
- **`patches/`** has the five commits on `a57e976`, authored `NeiroNext`
  with an `Assisted-by` trailer and the original messages (8857fce, 35212e3,
  a03eaab, 3da5047, 60ec176 in `~/work/b/nocsd-034`, branch
  `series-a57e976`, local).
- **All 16 combinations build** with upstream's flags: base, A, B, C, AB,
  AC, BC, ABC, D, AD, BD, CD, ABD, ACD, BCD, ABCD. Each has 0 warnings and
  0 errors, and libc is the only NEEDED library. ABCD also builds with
  Ubuntu's `dpkg-buildflags`, 0 warnings. Built on target2 with gcc 15.2.0
  (`logs/build-combinations.txt`).

## Re-measurement

target2 was brought to our repository the way a user would do it (key +
source, `full-upgrade`: unity `+unity11`, compiz `+unity2`, gtk-nocsd
`4.8-1+unity3`), plus the 44 applications from the archive. It ran a Unity
session with no `libunity-gtk4-menu`, as in the original runs. The scripts
are those of research/nocsd-gaps: `variant.sh`, `audit.py` and
`nocsd-desktops/breadth-any.sh`. `count.py` (this directory) counts the
old and the new audit files the same way (`logs/counts.txt`).

### Menus found and items that cannot be activated

The 44 names include Apostrophe, which opens no window with or without any
preload. So 43 applications are audited.

| variant | 6b1f70a, as recorded | 6b1f70a, recounted from its files | a57e976 |
|---|---|---|---|
| base, variable off | 0 | 0 | 0 |
| base: apps exporting / MISSING items | 35 / 38 | **34** / 38 | 33 / 38 (showtime: the audit's D-Bus call timed out on its slow start; it exports in every other run) |
| base + (a) | 35 / 2 | **34** / 2 | 34 / 2 |
| base + (a) + (b) | 42 / 10 | **41** / 10 | 41 / **3** |
| + (c), in Unity | 42 / 10 | **41** / 10 | 41 / 3 |
| + (d) (ABCD) | - / 3 | 41 / 3 | 41 / 3 |

- **An error in our own record.** research/nocsd-reply2 wrote 35 and 42
  "of 44". Its own files give 34 and 41: 43 audited applications, 9
  without a menu in base and 2 with (b). The record subtracted the apps
  without a menu from 44 and missed that Apostrophe is one of the 44. The
  figures on `a57e976` are the same as the recount: **34 → 41 of 43**.
- **(b) adds the same 7 applications:** simple-scan, gnome-calendar,
  epiphany, celluloid, gnome-2048, evince, gnome-firmware.
- **MISSING with (b) is 3, not 10.** Since research/nocsd-gaps, part (a)
  also covers action groups inserted on a widget. The same 3 items as
  there: Epiphany "Uninstall web app", Sudoku "Reset puzzle" before a game,
  Déjà Dup "Select all". The applications lack these actions at that
  moment too. The 10 items in 4 applications before that change are
  history (6b1f70a, logs of research/nocsd-reply2).
- The apps without a menu with (b): gnome-tour (no menu button) and
  gnome-contacts (fresh profile: the setup window has no menu).

**Epiphany** is measured on its own (`logs/var-epiphany-alone.txt`). In the
full runs an Epiphany instance left from the first run (variable off) kept
running. Every later launch handed its window to it over D-Bus and exited,
so the full-run files show `EXITED` for Epiphany. Alone, with that instance
killed first: no menu in base and (a); from (b) on its menu, with the one
MISSING item above.

### Items lost if the menu button were hidden

A debug build (ABCD plus one `fprintf` where `GTKNoCSDMenuClean` drops an
item with a custom widget; `logs/dropped-custom.txt`) drops items in **7
applications**: gnome-text-editor, kgx (Console), gnome-sudoku, loupe,
yelp, dialect, gnome-calendar. This is the same list as recorded.

### Menus that appear or change later (part (d))

`logs/late-menus.txt`:

| application | ABC | ABCD |
|---|---|---|
| Pinta 3.1.2 (built with dotnet-sdk-10.0) | no menu | its menubar (File, Edit, …) |
| Nautilus, after a rename | Undo keeps its old label | "Отменить переименование" (Undo Rename) |
| Papers, start page | the hidden sidebar menu (Open, Night mode, …) | its own menu: Shortcuts, Help, About |
| Papers, a PDF opened in the same window | sidebar menu | switches from the start menu to the sidebar menu |
| Papers, started with a PDF | sidebar menu | the document menu (Print, Fullscreen, Presentation, …) |
| Console (kgx) | a hidden page's menu: New Window, Fullscreen, Leave Fullscreen | New Window, Show All Tabs, Fullscreen, Preferences, Keyboard Shortcuts, About |

All as recorded in research/nocsd-gaps.

- The scripts get `GTK_NOCSD_GLOBAL_MENU=1` explicitly.
- The same-window Papers step was done by hand: the file chooser is a
  separate window, which `papers2.sh` did not activate, so its own run of
  that step opened nothing and is not counted.

### The holder on the Unity panel

With ABCD, Text Editor shows one panel entry with its name. A click opens
every item, with sections as separators (`shots/u-holder-panel.png`,
`shots/u-holder-open.png`).

### Not repeated

- **Plasma's Global Menu widget:** it needs a Plasma session on target2.
  The export is the same object as on Unity.
- **The flat variant:** an experiment branch, not part of the series.

### Crashes during the runs

- **Epiphany** SIGABRT once, at 18:17:38Z, in the first run (global menu
  off), about when the audited process (pid 5485) was being closed. Another
  Epiphany process (pid 5505) was running afterwards; it is the leftover
  instance above. Neither the abort nor where 5505 came from was
  investigated. The later separate runs showed no abort.
- **Showtime:** a Python `TypeError` in its own MPRIS handler (`mpris.py`,
  `None` in a D-Bus reply) during the debug run. That is the application's
  bug; it is not in the menu code.

## Result

- The series is on `a57e976`: `patches/`.
- All 16 combinations build.
- The re-measured figures match research/nocsd-gaps, except that our old
  "35 → 42" was off by one (34 → 41 of 43).
- The findings table of UNITY-20260927-038 has a new section with these
  results.

target2 is rolled back to `Clean-2` afterwards.
