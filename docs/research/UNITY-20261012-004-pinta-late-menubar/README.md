# unity-gtk4-menu: Pinta gets no global menu, its menu is built after realize (UNITY-20261012-004)

Owner: agent B (target2).

```yaml
task: UNITY-20261012-004
title: Pinta 3.1.2 gets no global menu on our packaged stack (no _GTK_MENUBAR_OBJECT_PATH)
found_in: UNITY-20261012-001 logs/03-mnemonics-start.txt (audit.py NO-MENUBAR, no _GTK_MENUBAR_OBJECT_PATH)
package: unity-gtk4-menu (0.9 live; 0.10, UNITY-20261012-006, changes no src/ code)
target_series: resolute
status: INVESTIGATING - code reading and the existing-fix check done; target confirmation waits for 0.10
```

## Reading the code

### unity-gtk4-menu 0.9 looks once, at realize

`src/unity-gtk4-menu.c` (0.9, `7ce9092`):

- **The hook.** `shim_window_realize` and `shim_app_window_realize` (:956-971) replace the realize class handler
  of GtkWindow and GtkApplicationWindow. Each calls `attach_menubar()` once, before chaining up to GTK's realize.
- **`attach_menubar()`** (:900-950):
  - It returns if the application already has a menubar of its own.
  - Otherwise it collects `GtkMenuButton` models (or the model of a `GtkPopoverMenu` popover) and
    `GtkPopoverMenuBar` models from the window's titlebar and child trees (`find_menu_model` :435,
    `collect_menus` :361).
  - It chooses one candidate, preferring shown, then primary, then the most app./win. items.
  - It builds a cleaned **copy** (`clean_model` :851), wraps it in a holder submenu labelled with the
    application's name, and calls `gtk_application_set_menubar`.
- **No menu found.** It logs "no menu model in this window" and returns.
- **Nothing later.** Nothing watches for menus added later: no retry, no emission hook, and no `items-changed`
  on the copied model.

### Pinta 3.1.2 builds its menu buttons after `Present()`

Tag 3.1.2, `b3df1e5`:

- **The menu exists first.** `Startup()` builds a menubar-shaped `Gio.Menu` (`_File`, `_Edit`, `_Layers`,
  `A_dd-ins`, `_Window`, `_Help`) before any window exists (`Pinta/MainWindow.cs:66-68`, `CreateMainMenu`
  :371-436).
- **The window is presented next.** `CreateWindow()` (:333-360) constructs `WindowShell`. Off macOS that is header
  bar mode: `IsUsingMenuBar()` reads the setting `menubar-shown`, default true only on macOS (:363-369).
  `WindowShell` builds an `Adw.ApplicationWindow` with an `Adw.HeaderBar` and calls **`Present()`** inside its
  constructor (`Pinta/WindowShell.cs:78`).
- **The buttons come last.** Only then does `CreateMainToolBar()` (:351, :438-476) pack five `Gtk.MenuButton`s
  into the header bar. The "Main Menu" button carries the model above.
- **So:** the window is realized, and unity-gtk4-menu's single look happens, before any menu button exists.
- **The setting.** With `menubar-shown=true` (View > Show/Hide > Menu Bar), Pinta calls `app.Menubar = menuBar`
  itself (:412) and uses a plain `Gtk.ApplicationWindow` with `ShowMenubar` (`WindowShell.cs:58-63`). GTK then
  exports the menubar natively. That path is not tested here.

### GTK 4.22.4: the properties are written at realize only

Local source `gtk4-4.22.4+ds` (4.22.4+ds-0ubuntu0.1):

- **Where they are written.** `gtk_application_impl_x11_handle_window_realize` (`gtk/gtkapplication-x11.c:41-65`)
  writes the six `_GTK_*` properties, including `_GTK_MENUBAR_OBJECT_PATH` (:56-61). It is called once per
  realize (`gtk/gtkwindow.c:4578` via `gtkapplication.c:1312`). Nothing else in GTK writes them.
- **No menubar, no property.** The value is the exported menubar's path. With no menubar it is NULL, and the
  property is deleted (`gdk/x11/gdksurface-x11.c:3115-3128`).
- **A later menubar does not reach the window.** `gtk_application_set_menubar` after realize (`gtkapplication.c:
  1014-1030`, `publish_menu` in `gtkapplication-dbus.c:468-503`) re-exports at `<app path>/menus/menubar`. It never
  writes any window's property.
- **Replacing is not changing.** Replacing the menubar model unexports the old exporter, and its subscribers get
  no `Changed` (glib 2.88.0 `gio/gmenuexporter.c`: `Changed` only for subscribed groups, :265; no signal on free,
  :710). Changing the same exported model (`items-changed`) does reach subscribers (:664).

## Existing-fix discovery (subagent, read-only, 2026-10-13)

- **gtk-nocsd's own menu code** (our series, `split-parts-2`, `a450853` "Find menus added late and follow menu
  changes", `Source/GTK-NoCSD.c`) handles this case. It is measured in UNITY-20260927-034 part (d): Pinta goes
  from no menu to File, Edit, … Help. How it works:
  - It sets an **empty `GMenu`** as the menubar before the window is realized (`GTKNoCSDMenuAttach` :5502, from
    `gtk_window_present` and the replaced realize). GTK therefore writes the property.
  - It **fills that same `GMenu` in place** later, so the path and the subscribers stay.
  - It **retries** the search every 250 ms, up to 12 times (`GTKNoCSDMenuRetry` :5490).
  - It follows `items-changed` on the source model (`GTKNoCSDMenuWatch` :5277).
  - A `map` emission hook on GtkMenuButton (`GTKNoCSDMenuFollowShown` :5420) searches again.
  - When every top-level item is a submenu, as with Pinta, it puts the items on the panel without a holder
    (`GTKNoCSDMenuShaped` :5311).
  - A window that never finds a menu keeps an empty menubar, which shows nothing on the panel (research/nocsd-gaps,
    gnome-tour).
  - The released gtk-nocsd 4.8 that we ship has none of this code (UNITY-20261012-001, section (b)).
- **appmenu-gtk-module** (GTK3; ours 25.04-1build1+unity1) and **unity-gtk-module** (upstream
  0.0.0+18.04.20171202):
  - They export a per-window container `GMenu` on their own path at window realize, and write
    `_GTK_MENUBAR_OBJECT_PATH` themselves, even while the container is empty (appmenu `src/platform.c:90-240`,
    `src/hijack.c:69-99`).
  - A GtkMenuBar realized later is caught by a menubar class realize hook and appended to the container, so
    subscribers get `Changed` (`hijack.c:131-146`, `src/datastructs.c:206-249`).
- **unity-gtk4-menu** has no upstream besides ours (github.com/Ubuntu-Unity-LifeSupport/unity-gtk4-menu).
  `git ls-remote` at 2026-10-13 01:28Z shows main at `7ce9092` (0.9) and branch `a/UNITY-20261012-006` at
  `aa00846` (0.10). There is nothing newer than 0.10.
- **Pinta:**
  - No issue about Unity or GTK4 appmenu.
  - Related: #781 (classic menubar, closed 2025-06-25), PR #1418 (the menubar layout, merged 2025-05-15), #1951
    (KDE Global Menu, open; a comment says it works on X11 with Pinta's menubar option on).

## Not yet done

- **Target confirmation.** The library's `note()` log for Pinta on target2 should show "no menu model in this
  window" at realize, with the MenuButtons appearing after it. This waits for 0.10 (UNITY-20261012-006) to be
  published and merged, on C's word.
- **Unknown:**
  - whether unity-panel-service re-reads `_GTK_MENUBAR_OBJECT_PATH` when it appears on an already-mapped window;
  - whether Pinta with `menubar-shown=true` works on our stack.
- **The component question,** before any design (CLAUDE.md): gtk-nocsd's menu code already handles late menus,
  but we do not ship it. The architecture question between gtk-nocsd and unity-gtk4-menu is open with May
  (DECISIONS 2026-09-25).
- **Design Challenger** before any code. A owns the unity-gtk4-menu packaging; C is told before the design.
