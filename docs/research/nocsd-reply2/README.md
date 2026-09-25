# Global menu in gtk-nocsd: measurements after the maintainer's second reply

Agent B, 2026-09-25, on `target2` (rolled back to `Clean-2` afterwards). The
questions come from gtk-nocsd's maintainer's reply on issue #1 (2026-09-25
17:13Z); this directory is measurements only. Nothing was sent anywhere.

The maintainer's current implementation is not published (codeberg: only
`main` at 6b1f70a, no branches, no pull requests), so it could not be
compared with ours; everything below is ours measured on its own.

target2 for these runs: our aptly packages (unity `+unity9`, compiz
`+unity2`, ...), Unity session, then a Plasma 6.6.4 X11 session with the
Global Menu widget for the KDE rows.

## 1. The holder menu

Our export puts the whole header bar menu into one submenu named after the
application (the "holder"). Compared on the panel with a native GTK4
menubar (`tests/menubar4.c`: File/Edit/Help set with
`gtk_application_set_menubar`), a GTK3 `GtkMenuBar` exported by
appmenu-gtk-module (`tests/menubar3.c`), and a "flat" build that sets the
cleaned model itself as the menubar (experiment only, not in any patch):

| | Unity 7 panel | Plasma Global Menu widget |
|---|---|---|
| native GTK4 menubar | File, Edit, Help | File, Edit, Help |
| GTK3 GtkMenuBar (appmenu-gtk-module) | File, Edit, Help | File, Edit, Help |
| our holder | one entry (the app name); a click opens every item, sections as separators | same: one entry, opens the full list with separators |
| flat | every item a panel entry; separators lost; the list does not fit the panel; a click on an entry opens a one-row submenu "Activate" | every item a panel entry, pushing the task manager aside; a click runs the item directly |

`shots/u-open.png`, `shots/u-flat.png`, `shots/k-panels.png`,
`shots/k-click.png`. Both panels open the holder on click; neither turns
its items into top-level entries. A header bar menu has no File/Edit
structure of its own, so there is nothing to put at the top level except
the items themselves - which is the flat row above.

## 2. Menus not found

Our version (the full patch) over 44 GTK4 applications: the 18 of
`research/layer-b/` plus 26 more from the 26.04 archive
(`breadth-ext.txt`, `var-*.txt`).

- 42 of 44 export a menu. The two that do not: gnome-tour has no menu
  button; gnome-contacts on a fresh profile first shows its setup window
  (`did-initial-setup` false), which has no menu.
- apostrophe opens no window at all, with or without any preload - a Python
  error in the application (`'ApostropheTextView' object has no attribute
  'markup'`); not counted.
- 10 items are exported but cannot be activated ("MISSING" in the audit):
  epiphany 6 (`win.*` from a group it inserts itself), gnome-2048 2
  (`ui.*`), gnome-sudoku 1 (`game-view.*`), deja-dup 1 (`restore.*`). All
  are action groups inserted on a widget with
  `gtk_widget_insert_action_group`; the proxy covers class actions only.
  unity-gtk4-menu 0.9 has the same gap.
- Items disabled by the application's own state (evince with no document:
  14) are exported disabled, as in its own popover.

## 3. GTK3 applications with a header bar menu

10 GTK3 applications with a menu button (gnome-disks, gnome-connections,
gnome-taquin, gnome-tetravex, four-in-a-row, five-or-more, hitori,
gnome-klotski, dconf-editor, seahorse) plus `tests/hamburger3.c`: our code
does nothing for them (it hooks GTK4 only). No global menu entry, the menu
button stays in the window and works, no crash. appmenu-gtk-module puts an
empty menubar path on such windows. `breadth-gtk3.txt`, `shots/u-gtk3.png`.

## 4. The patch split into parts

`patches/` - four commits on gtk-nocsd `main` (6b1f70a), authored
`NeiroNext`, `Assisted-by` trailer, formatted with upstream's Uncrustify
config, 0 warnings with upstream's flags:

1. **Base (a stand-in for the maintainer's own)** -
   `GTK_NOCSD_GLOBAL_MENU=1` enables it, off by default; finds the main menu
   and sets it as the application's menubar from the `gtk_window_present`
   hook, before the window is realized. No cleaning, no realize, no setting.
2. **(a) Cleaning and proxies** - items with a custom widget dropped,
   stand-ins for class actions and property actions, the
   `gtk_widget_action_set_enabled` hook. Its functions are loaded by their
   own function with their own readiness check.
3. **(b) realize replacement** - for windows that are not presented.
4. **(c) gtk-shell-shows-menubar** - export only while the shell shows
   menubars, withdraw when it stops.

`split/gen.py` builds any combination from one marked-up source; all eight
(base, A, B, C, AB, AC, BC, ABC) build with 0 warnings, libc the only NEEDED
library. So (a) can be taken without (b) and (c); the commits as ordered
apply in sequence, other combinations come from the generator.

Measured over the same 44 applications, with `GTK_NOCSD_GLOBAL_MENU=1`
(`var-*.txt`):

| | menus exported | items that cannot be activated |
|---|---|---|
| base without the variable | 0 | - |
| base | 35 | 38 |
| base + (a) | 35 | 2 |
| base + (a) + (b) | 42 | 10 (the groups of item 2) |
| + (c), in Unity | 42 | 10 |

- (a) is what makes the exported menus usable: 38 dead items to 2 on the
  same 35 applications.
- (b) adds the 7 applications that never pass `gtk_window_present`
  before realize: simple-scan, gnome-calendar, epiphany, celluloid,
  gnome-2048, evince, gnome-firmware.

**Correction of our own earlier claim.** The patch previously said, in code
comments and in `research/nocsd-desktops/`, that without
`gtk-shell-shows-menubar` GTK would draw the exported menubar in the window,
next to the menu button. For GTK4 that is not so:
`GtkApplicationWindow:show-menubar` defaults to FALSE in GTK 4.22.4
(`tests/mbtree.py`: no menubar widget in the window; with
`show-menubar=TRUE` a `PopoverMenuBar` appears). With the base alone and the
flag off, the menu is exported and nothing changes in the window
(`shots/inwin-ct.png`). Part (c) therefore only avoids exporting where
nothing reads it; the comments were corrected.

How the button choices fit this scheme (facts, no choice made):

- **Keep the button** (what the parts do now): the menu is in both places;
  nothing is lost.
- **Hide the button** when exported: 7 of the 44 applications would lose
  items that embed a widget, since those cannot be exported -
  gnome-text-editor (theme, zoom), gnome-console (theme switcher, zoom),
  gnome-sudoku (fullscreen, zoom in/out), loupe (rotate left/right), yelp
  (zoom), dialect (theme), gnome-calendar (weather). Measured by a debug
  build logging each dropped item. If the button is hidden it has to come
  back when the export is withdrawn ((c)).
- **An item "open the original menu"**: would open the popover from the
  menu button, so it needs the button in the window (a hidden button has
  nowhere to anchor its popover); not built.
- **Menubar in the window**: not a side effect of exporting (see the
  correction). It takes `show-menubar=TRUE` on the window; GTK then draws
  the menubar in the window and hides it by itself where the shell shows
  menubars.

## 5. Two gtk-nocsd findings not reported, re-checked on main

- **gnome-sound-recorder crash with gtk-nocsd alone** - not on current
  code. With a fresh D-Bus session per run: the 26.04 archive's March
  snapshot (`3+0~20260321+0b77e1b-1`) SIGSEGV; release 4.8 alive 3/3; main
  6b1f70a alive 3/3; no preload alive 3/3. Fixed by 4.8.
- **GTK types never fetched when GTK4 is first seen in a
  `GetTypes=false` call** - reproduced on main 6b1f70a with
  `tests/typesorder.c`, traced with `tests/trace.gdb`. The program creates a
  GObject before GTK is loaded (`g_object_new` hook: `GetReferences(true)`
  with no GTK, `GotTypes` becomes true), then `dlopen`s GTK4 and gets its
  functions with `dlsym`, as Gir.Core does: GTK4 is first seen in
  `GetReferences(false)` from the type-registration hook, the version
  becomes 4 without fetching types, and every later `GetReferences(true)`
  returns early because the version did not change -
  `GTKNoCSDGTKWindow` stays 0. Without the early GObject (control run) the
  types are fetched. Condition at `GTK-NoCSD.c:1324` on main.
- **environment.d not applied under Xfce** (Debian packaging) - measured
  2026-09-25 with Xfce 4.20 and Debian's 4.8-1 packaging
  (`research/nocsd-desktops/`): xfce4-session, xfce4-panel and xfdesktop run
  without `LD_PRELOAD`, so applications started from Xfce do not load
  gtk-nocsd. It is about how the Xfce session starts, not gtk-nocsd's code,
  so main does not change it; not re-run.
