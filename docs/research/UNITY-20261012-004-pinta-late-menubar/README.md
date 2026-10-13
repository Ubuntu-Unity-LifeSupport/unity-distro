# unity-gtk4-menu: Pinta gets no global menu, its menu is built after realize (UNITY-20261012-004)

Owner: agent B (target2).

```yaml
task: UNITY-20261012-004
title: Pinta 3.1.2 gets no global menu on our packaged stack (no _GTK_MENUBAR_OBJECT_PATH)
found_in: UNITY-20261012-001 logs/03-mnemonics-start.txt (audit.py NO-MENUBAR, no _GTK_MENUBAR_OBJECT_PATH)
package: unity-gtk4-menu (0.9 live; 0.10, UNITY-20261012-006, changes no src/ code)
target_series: resolute
status: INVESTIGATING - root cause confirmed on target2 (0.9); the choice of fix goes to C and May
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

## Target confirmation (target2, 2026-10-13, logs/02)

The setup (`setup.sh`, logs/01):
- **Restore:** Clean-2, confirmed inside the guest.
- **Live archive:** Release Date 2026-10-13 00:03:25 UTC.
- **Packages:** libunity-gtk4-menu0 0.9, libgtk-nocsd0 4.8-1+unity4, unity +unity13.
- **Pinta:** 3.1.2 (`b3df1e5`), built with dotnet-sdk-10.0 10.0.112.
- **Session:** one cold session. Pinta was started in its environment by `run.sh`, with unity-gtk4-menu's debug
  log (`UNITY_GTK4_MENU_DEBUG=1`).

0.10 has the same `src/` code, so the result carries over to it.

**Default, header bar mode (p1).**
- The library hooks realize at 01:50:46.459.
- At 01:50:57.325, during realize, it logs **"no menu model in this window"**. The window is mapped at
  01:50:59.550.
- The window has no `_GTK_MENUBAR_OBJECT_PATH`, `audit.py` reports `NO-MENUBAR`, and the panel service has no
  entry for the window.
- The screenshot shows Pinta's header-bar buttons, and the panel shows only the title.
- So it is confirmed: the library's one look happens before Pinta's menu buttons exist.

**Pinta's own setting `menubar-shown=true` (p2), same session.**
- The library logs **"the application already has a menubar"**, because Pinta set `app.Menubar` itself.
- GTK writes `_GTK_MENUBAR_OBJECT_PATH=/com/github/PintaProject/Pinta/menus/menubar`.
- The panel service holds 10 entries: `_File`, `_Edit`, `_View`, `_Image`, `_Layers`, `_Adjustments`,
  `Effe_cts`, `A_dd-ins`, `_Window`, `_Help`. The panel shows them on hover, and audit.py counts 111 labels.
- No in-window menubar is visible.
- A user who turns that setting on (View > Show/Hide > Menu Bar) gets the full global menu today, with no
  change of ours.

## Inputs for the decision (subagent, read-only, 2026-10-13; estimates are marked)

### A minimal unity-gtk4-menu change (ESTIMATE)

**What it would do:**
- Always set an empty holder `GMenu` at realize (`attach_menubar` :900), so that GTK writes the property, then
  fill it in place.
- Add a bounded retry (gtk-nocsd uses 250 ms × 12) or a hook on GtkMenuButton (realize, or a `map` emission
  hook).
- Add a "menubar-shaped" check, so that Pinta's File…Help go on the panel without the holder.
- Optionally follow `items-changed`, because `clean_model` makes a static copy (:839-851). Nautilus, Papers and
  Console need that, see below.
- Resolve about 6-8 more symbols in `resolve_all` (:187).

**Size:** about 80-120 lines for the Pinta case, and about 200-250 lines for parity with the gtk-nocsd late-menu
commit. That commit, `a450853`, is +277/−25. Finding, cleaning, labelling and the proxies already exist here.

**A shelved prototype exists:** `docs/research/layer-b/late-menu-placeholder.diff`, about +74/−9 against an older
unity-gtk4-menu. It sets an empty menubar at realize and fills it from a realize hook on GtkMenuButton and
GtkPopoverMenuBar. DECISIONS 2026-09-24 (around line 800) shelved it on purpose: no application was known then
to need it, and it exports empty menubars for applications with no menu. An empty menubar shows nothing on the
panel (research/nocsd-gaps, gnome-tour). It was never measured on Pinta.

### Moving to the gtk-nocsd menu code

**Upstream already carries our late-menu code.**
- GTK-NoCSD main has our five menu commits as `3b1d4a3..2d50fe9` (2026-09-28, author NeiroNext).
- `2d50fe9` has the same patch-id as our `a450853`.
- Upstream's maintainer has reworked it since: `092e184`, …, `b76f3fb`, `7f49f81`, `fd4b76a`.
- `fd4b76a` still has the late-menu functions (Retry, Waited, Watch, FollowShown, ButtonMap, Fill, Put; around
  :4002-4350). Shaped became `GTKNoCSDMenuGrouping`, and the switch is `GTK_NOCSD_MENU`.

**What we ship.** The shipped gtk-nocsd 4.8 has no menu code. Shipping upstream's means a 4.8+git snapshot:
4.8..`fd4b76a` is 50 commits, +2313/−512 in GTK-NoCSD.c. Our series on its own sits on `6b1f70a`, 25 commits
above 4.8. Whether it applies to 4.8 was not tested: the guard refused the scratch apply test, a broad
`git add -A`, and it was not retried.

**Differences between the two libraries:**
- **Only in upstream gtk-nocsd:** late menus, following changes, inserted action groups, GTK3 menus.
- **Only in unity-gtk4-menu:** on by default under Unity (`XDG_CURRENT_DESKTOP`, :973), a gsettings label, and
  glibc's versioned `dlsym` (the issue #1 fix).
- **Neither** has per-window menus.
- **Constraint:** if upstream's menu code is shipped, `GTK_NOCSD_MENU=1` must be set for Unity sessions only
  (UNITY-20261012-001, (b)), and the two libraries must not both export a menu.

**An earlier, different option was rejected:** building unity-gtk4-menu into our gtk-nocsd package as a 1250-line
carried patch (DECISIONS, the "unity-gtk4-menu inside gtk-nocsd" entry).

### Other applications (research/nocsd-gaps, UNITY-20260927-034 logs/late-menus.txt)

- **No menu at all with a realize-only look:** Pinta 3.1.2. gnome-contacts' first-start setup window opens the
  main window as a second realize, which 0.7 and later already handle.
- **A stale or wrong menu with a copy at realize:**
  - Nautilus: Undo is relabelled after a rename.
  - Papers: the start view, the document view, and a PDF opened in the same window. At realize the hidden
    sidebar's menu is chosen.
  - Console (kgx): a hidden page's menu.
  - Epiphany: items removed after realize, from a code comment only, not measured.
- How unity-gtk4-menu 0.9 itself behaves on Papers and Console has not been measured.

## Not yet done

- **For C and May,** with no design until then: a small unity-gtk4-menu change, or moving to the upstream
  gtk-nocsd menu code. That is the architecture question open since DECISIONS 2026-09-25.
- **Whatever is chosen:** the Design Challenger before any code. A owns the unity-gtk4-menu packaging.
