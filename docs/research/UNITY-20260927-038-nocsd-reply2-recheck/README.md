# UNITY-20260927-038: our GTK-NoCSD findings, re-checked on the current main

Owner: agent B. This re-checks the findings about GTK-NoCSD in
`research/nocsd-reply2/`, `research/nocsd-gaps/` and
`research/nocsd-epiphany-crash/`, which were measured on main `6b1f70a`,
against the current main of codeberg MorsMortium/GTK-NoCSD.

- **Main checked:** `e817d80`. On 2026-09-28 main was already at `a57e976`,
  two commits later ("Missing warnings", "Reset theme right before GTK
  init"); every run below was made on both.
- **Commits since `6b1f70a`:**
  - `af90f21`: dialog title;
  - `249fc46`: sections; drops `GTKNoCSDAboutClose` and
    `GTKNoCSDFindWindowTitle`;
  - `5aba1d3`: LibAdwaita-only CSS;
  - `2cdf402`: the settings setup moves out of `GTKNoCSDMagic` into the new
    `GTKNoCSDDoSettings`, also for inspector windows;
  - `607c3a4`, `e817d80` (README), `a66ff8c`, `a57e976`.

  None of them changes a line that mentions a menu.
- **Where it ran:** target2, Unity session, GTK 4.22.4, GTK 3.24.52. Four
  builds of GTK-NoCSD with its Makefile, 0 warnings each: `6b1f70a`,
  `2cfc8f1` (our fix), `e817d80`, `a57e976`.

**Outcome.**

- **The Epiphany Passwords abort** is fixed on main by `af90f21`
  (2026-09-26), with the same code as our fix.
- **The types bug** still reproduces.
- **Our global-menu series** no longer applies to main as it is.
- **The menu figures** measure that series. They are re-measured once it is
  carried over (UNITY-20260927-034).

## Findings

Status values:

- **holds** (checked now);
- **no longer holds**;
- **after 034**: not checkable until our series is carried to the current
  main; re-measured in UNITY-20260927-034.

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Holder menu: on Unity and Plasma's Global Menu one entry with the app's name; a click opens the list with sections as separators | after 034 | A property of our export, measured on `6b1f70a` (research/nocsd-reply2 §1, shots). The commits since change no menu code, so there is no known reason for it to change. |
| 2 | Flat variant: every item a separate panel entry, separators lost, a long menu did not fit; on Unity a one-row "Activate" submenu | after 034 | As #1 (`exp-flat`, research/nocsd-reply2 §1). |
| 3 | Our series is enabled by `GTK_NOCSD_GLOBAL_MENU=1`, off by default | holds (for the series as it is) | `0001-Export-...patch` reads the variable (4 mentions). |
| 4 | The cleanup part loads its own symbols and builds without the realize and settings parts | after 034 | True on `6b1f70a` (split/gen.py: all 8 combinations build). On `e817d80` part (a) conflicts in the `LOAD_SYMBOL` list with the new `gtk_widget_add_css_class`/`gtk_settings_get_for_display` (a mechanical conflict). |
| 5 | 44 GTK4 apps: a hook on present finds 35 menus; replacing realize brings it to 42 | after 034 | Measured on `6b1f70a` (research/nocsd-reply2 §2, var-*.txt). `2cdf402` rewrote the settings part of `GTKNoCSDMagic`, next to our parts (b) realize and (c) settings, so the numbers cannot be carried over by reasoning. |
| 6 | Late menus: Pinta got no menu, Papers switches menus, Nautilus relabels Undo, Console exported a hidden page's menu; with deferred lookup plus tracking all four are right; not covered: two menus at once, per-window menus | after 034 | Part (d), research/nocsd-gaps. |
| 7 | GTK4 `show-menubar` defaults to FALSE, GTK3 to TRUE | holds | target2, via gi: `Gtk.ApplicationWindow` `show-menubar` default **False** in GTK 4.22.4, **True** in GTK 3.24.52. The exported menubar with `show-menubar=TRUE` remains untested. |
| 8 | Hiding the menu button loses items in 7 of 44 apps (theme and zoom in Text Editor and Console, rotation in Loupe, weather in Calendar, and others) | after 034 | Depends on the apps' own menus; measured by our debug build on `6b1f70a` (research/nocsd-reply2 §4). |
| 9 | A "show the original menu" item needs the menu button visible, since the popover is anchored to it | holds | A GtkMenuButton's popover is anchored to the button. Reasoning, not measured (research/nocsd-reply2 §4: not built). |
| 10 | Inserted action groups: 10 items in 4 apps (Epiphany, 2048, Sudoku, Déjà Dup) were inert; tracked since; 3 items across 44 still cannot be activated, and the app lacks the action then too | after 034 | Measured on `6b1f70a` + our series (research/nocsd-gaps). |
| 11 | Our series covers GTK4 only | holds | On main, GTK3 menu handling is `gtk_application_set_app_menu(Application, NULL)` for CSD apps (GTK-NoCSD.c:2859-2863). |
| 12 | Of 10 GTK3 apps with a menu button, 9 use a GMenuModel | holds (as measured) | research/nocsd-reply2 §3, breadth-gtk3.txt; about the apps, not GTK-NoCSD. Not re-run. |
| 13 | The gnome-sound-recorder crash is fixed since 4.8 | holds | research/nocsd-reply2 §5: archive snapshot SIGSEGV, 4.8 and `6b1f70a` alive 3/3. The later commits do not touch that path. Not re-run (the app is not on Clean-2). |
| 14 | A GObject created before GTK is loaded sets `GotTypes` with no types; if GTK4 is then first seen in a `GetTypes=false` call, `GTKNoCSDGTKWindow` stays 0 | **holds** | logs/03: `typesorder` under gdb. With the early GObject, at exit `version=4 gottypes=1 GTKNoCSDGTKWindow=0` on `6b1f70a`, `e817d80` and `a57e976`. The control run (no early object) fetches the types. The early-return condition is unchanged (GTK-NoCSD.c:1344 on `e817d80`). |
| 15 | Real Gir.Core apps (Pinta 3.1.2) do not hit #14: they load GTK first | holds (as measured) | research/nocsd-gaps ("Gir.Core"): Pinta 3.1.2 and GcMenu fetch the types on `6b1f70a` (gdb). The code path is unchanged on main. Not re-run. |
| 16 | Epiphany aborts when opening Passwords on main | **no longer holds** | Fixed by `af90f21` "Only set title on dialogs once and do not set width of not existing header" (2026-09-26). logs/01: `dialogtitle dialog`, 3 runs each: `6b1f70a` SIGABRT 3/3 (critical in `gtk_widget_get_preferred_size`); `e817d80` and `a57e976` exit 0 3/3, with the title "Passwords". **Epiphany itself not tested** (not installed on Clean-2); the proof is the reproducer. |
| 17 | The abort was introduced by `8f076dd` | holds (history) | `8f076dd` "Disregard window title set from library when checking if title was set"; bisect in research/nocsd-epiphany-crash. |
| 18 | Mechanism of #16 | holds (history) | research/nocsd-epiphany-crash. `af90f21` changes exactly the two points found there, which confirms the mechanism. |
| 19 | Our fix `2cfc8f1` | same as upstream | Our `2cfc8f1` and `af90f21` are the same code; only the comments differ (both: `Parent == NULL ||` added to `HasTitle`, size request under `if (Parent != NULL)`). `dialogtitle.c` is 93 lines. |
| 20 | The Mahjongg behaviour (window title follows a changing header label) is kept | holds, also for `af90f21` | logs/02: `dialogtitle clock`, the window title follows the label (00:01..00:04) on all four builds. GNOME Mahjongg itself not run. |
| 21 | Our series (base stand-in, cleanup, realize, setting, late menus) applies to main; every combination builds without warnings | **no longer holds** | `git am` of research/nocsd-gaps/split/patches onto `e817d80` fails at 0001. With `-3`, 0001 applies and 0002 conflicts in the `LOAD_SYMBOL` list. True for `6b1f70a` only. Carrying the series over is UNITY-20260927-034. |
| 22 | Open upstream bugs from our findings | one left | #16 is fixed upstream; #14 is still open. |
| 23 | research/nocsd-gaps is reachable on GitHub | holds | HTTP 200 on 2026-09-28. |
| 24 | Main has no global-menu export of its own | holds | No menu export on `e817d80` or `a57e976` (grep: no GMenuModel export, no menubar code). |
| 25 | Our package: environment.d does not reach Xfce, fixed via Xsession.d | holds, since +unity3 | 4.8-1+unity2 added `/etc/X11/Xsession.d/51gtk-nocsd`. 4.8-1+unity3 (2026-09-26) fixed that script's regression: it replaced the environment.d value and dropped `libunity-gtk4-menu.so.0` in Unity sessions. 4.8-1+unity3 is the newest published version (the published `Packages` index, read as a file). |

## Re-measurement on main a57e976 (UNITY-20260927-034, 2026-09-28)

Our series carried over to main `a57e976` (research/UNITY-20260927-034-nocsd-series-port):
all 16 combinations build with 0 warnings, and the figures were measured
again on target2 by the same scenarios. The rows marked "after 034":

| # | Finding | Status on `a57e976` | Evidence |
|---|---|---|---|
| 1 | Holder menu on the panel | holds on Unity; Plasma not repeated | Text Editor: one panel entry with its name, a click opens every item with sections as separators (034 `shots/u-holder-*.png`). |
| 2 | Flat variant | not repeated | An experiment branch, not part of the series. |
| 4 | The parts build independently | holds | All 16 combinations (base, A, B, C, AB, AC, BC, ABC, D, AD, BD, CD, ABD, ACD, BCD, ABCD): 0 warnings, libc only (034 `logs/build-combinations.txt`). |
| 5 | Present finds 35 menus, realize brings 42 | **correct figures: 34 → 41 of 43** | The 44 applications include Apostrophe, which opens no window, so 43 are audited. The earlier files on `6b1f70a` give 34 and 41 as well; "35 → 42" was an off-by-one in our record. `a57e976`: base 33 (Showtime's slow start timed out the audit; it exports in every other run), (a) 34, (b) 41, the same 7 applications added by (b) (034 `logs/counts.txt`). |
| 6 | Late menus: Pinta, Papers, Nautilus, Console | holds | With (d): Pinta 3.1.2 its full menubar, Nautilus "Undo Rename", Papers start / same-window / file-start menus, Console its main menu; without (d) as described (034 `logs/late-menus.txt`). |
| 8 | Hiding the button loses items in 7 of 44 apps | holds | A debug build logs dropped custom-widget items in the same 7 applications (034 `logs/dropped-custom.txt`). |
| 10 | Inserted groups: 10 items in 4 apps before; 3 left | holds | Before the groups change (`6b1f70a` files): 10 in 4. Now, from (b) on: 3 (Epiphany "Uninstall web app", Sudoku "Reset puzzle" before a game, Déjà Dup "Select all"), missing in the applications too. |
| 21 | The series applies to main | holds again, as a new series | `patches/` of 034: five commits on `a57e976`. |

## Unknowns

- The rows marked "after 034" are re-measured in the section above. Not
  repeated there: Plasma's Global Menu widget (#1) and the flat variant (#2).
- Epiphany itself was not run on the fixed main; the evidence is the
  reproducer (#16).
- #12, #13 and #15 were not re-run (the apps are not on Clean-2). Their code
  paths are unchanged on main.

## Method

- `tests/dialogtitle.c`, `tests/rep.sh` are from
  research/nocsd-epiphany-crash.
- `tests/typesorder.c`, `tests/trace.gdb` are from research/nocsd-reply2.
- Builds: `git archive` of each commit, `make` on target2 (build-essential
  and libadwaita-1-dev installed for the test; target2 rolled back to
  `Clean-2` afterwards).
