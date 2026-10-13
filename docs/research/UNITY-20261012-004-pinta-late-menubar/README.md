# unity-gtk4-menu: Pinta gets no global menu, its menu is built after realize (UNITY-20261012-004)

Owner: agent B (target2).

```yaml
task: UNITY-20261012-004
title: Pinta 3.1.2 gets no global menu on our packaged stack (no _GTK_MENUBAR_OBJECT_PATH)
found_in: UNITY-20261012-001 logs/03-mnemonics-start.txt (audit.py NO-MENUBAR, no _GTK_MENUBAR_OBJECT_PATH)
package: unity-gtk4-menu (0.9 live; 0.10, UNITY-20261012-006, changes no src/ code)
target_series: resolute
status: VERIFYING - unity-gtk4-menu 0.12 (variant A, design APPROVE round 3) built and tested on target2 (2026-10-13)
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

## Is there a more elegant way than a retry timer? (subagent, read-only, 2026-10-13)

The question came from the decision on the fix. Sources are cited inline; the subagent's scratch clones are not
kept.

### Precedents: none of them uses a timer

- **unity-gtk-module** (GTK2/3, `0.0.0+18.04.20171202`, `src/main.c`):
  - It overrides class `realize` of GtkWindow, GtkApplicationWindow and GtkMenuBar (:550-635, :760-866).
  - At window realize it exports an **empty per-window GMenu** and writes `_GTK_MENUBAR_OBJECT_PATH` itself
    (:367-428).
  - A GtkMenuBar realized later is appended to that menu. Later changes follow GtkMenuShell `insert`.
- **appmenu-gtk-module** (ours, 25.04-1build1+unity1) is the same design: realize hooks (`src/hijack.c:69-163`),
  an empty GMenu exported at realize with the property written by XChangeProperty (`src/platform.c:90-220`), late
  menubars appended in place (`src/datastructs.c:239`).
- **vala-panel-appmenu** ships the same GTK module and has no GTK4 support.
- **KDE Plasma** (`gmenu-dbusmenu-proxy`, `menuproxy.cpp:271-326`) reads the `_GTK_*` properties once, when the
  window is added. It relies on "an empty menubar announced at realize, filled later" (`window.cpp:204`).
- **Our gtk-nocsd series `a450853`:** the 250 ms × 12 retry is the only part that finds a menu that does not exist
  yet at realize, which is Pinta's case. Its `map` hook and its `items-changed` watch are installed only after the
  first menu has been found (`GTKNoCSDMenuFill`, `GTKNoCSDMenuFollowShown` :5420-5434).

### An event-driven variant for GTK 4.22

**Which hooks are available** (glib 2.88.0, GTK 4.22.4):
- GtkWidget `map` and `realize` take emission hooks (`gtkwidget.c:1743`, `:1782`).
- `GObject::notify` is `G_SIGNAL_NO_HOOKS` (`gobject.c:1083`), so `notify::menu-model` can be followed only per
  instance.
- `root`/`unroot` are vfuncs only, not signals.

**Pinta's case is caught by `map`.** Pinta passes the `MenuButton` with its `MenuModel` already set to
`adw_header_bar_pack_end` → `gtk_box_prepend`. That maps the button synchronously, because the header bar is
already mapped (`gtkwidget.c:6336-6342`, `:2974`).

**Interposing the setters would not catch it.** GTK links with `-Bsymbolic`, so its internal calls never go
through the PLT. .NET resolves its calls with `dlsym` on libgtk's own handle, which does not include our library.

**So the variant would be:**
1. At realize, set an empty GMenu as the menubar.
2. Install one `map` emission hook up front. It filters for GtkMenuButton and GtkPopoverMenuBar whose window is
   still waiting, then coalesces through one idle.
3. For a mapped button without a model, connect per-instance `notify::menu-model` and `notify::popover`.
4. After the first fill, keep following `items-changed`.

No case needing a timer was found. A menu in a widget that is never mapped stays uncaught, but the user cannot see
that menu either.

### Upstream options

- **GTK.** No issue or MR was found about writing `_GTK_MENUBAR_OBJECT_PATH` when `set_menubar` comes after
  realize. GitLab search could not be read, so this is UNKNOWN.
  - The change would be about 30-40 lines in `gtkapplication-x11.c`, plus Wayland.
  - It only helps panels that re-read the property: KDE does not, and Unity is UNKNOWN.
- **Pinta.** No issue asks for `app.Menubar` in header-bar mode. Related: #781 (closed by PR #1418) and #1951
  (open; the maintainer: "Pinta's really just relying on GTK doing the right thing here").
  - `AdwApplicationWindow` forces `show-menubar` off (libadwaita `adw-application-window.c:298`), so exporting
    the menubar would add no in-window bar.
  - The header-bar model leaves out View, Image, Adjustments and Effects (`MainWindow.cs:396-405`), so a full
    model would have to be built: about 10-20 lines.

### The empty menubar

- **On the panel:** an empty menubar shows nothing until it is filled (research/nocsd-gaps, gnome-tour), and GTK
  shows no in-window bar for 0 items (`gtkapplicationwindow.c:218`).
- **Side effect:** `gtk_application_get_menubar()` is no longer NULL. An application that sets its own menubar
  later replaces ours, and `a450853` guards against that.
- **Writing the property after realize:** possible with the deprecated `gdk_x11_surface_set_utf8_property`, but
  without a confirmed benefit.

### Variants (estimates)

| variant | where | event-driven | size | risk | Pinta's default mode |
|---|---|---|---|---|---|
| A: empty GMenu at realize + `map` hook + per-instance notify + `items-changed` | unity-gtk4-menu | yes (one idle) | ~150-200 lines | low-medium: one global hook with a type filter | yes |
| B: a450853-style retry 250 ms × 12 | unity-gtk4-menu | no | ~250 lines | medium: 3 s limit, polling | yes, within 3 s |
| C: GTK writes the property on a later `set_menubar` | GTK | yes | ~30-40 lines + Wayland | upstream timeline; needs a panel that re-reads | only if the panel re-reads |
| D: Pinta exports its menubar in header-bar mode | Pinta | - | ~10-20 lines | acceptance unknown, no issue exists | yes |
| E: gtk-nocsd's menu code (`a450853`) | gtk-nocsd | partly (retry) | +277 (exists) | timer; duplicates unity-gtk4-menu | yes, within 3 s |

UNKNOWN:
- whether Unity's indicator-appmenu re-reads the property on PropertyNotify;
- what the HUD shows for an empty menubar filled later;
- whether Pinta's "Main Menu" button wins the candidate ranking (inferred from the scoring, not measured).

## Design review round 1 (Design Challenger, 2026-10-13): REVISE

The design is in DESIGN.md (round 1 at `92666f6`).

**Confirmed:**
- `attach_menubar` runs before the chain-up, and `publish_menu` sets the path synchronously
  (`gtkapplication-dbus.c:468-503`), so `gtkwindow.c:4578` writes the property for that same window.
- `gtk_window_show` maps synchronously, so Pinta's buttons are mapped while still inside its constructor.
- `map` is emitted through `g_signal_emit` (`gtkwidget.c:2974`).
- Everything runs on the main thread.

**Blocking:**
1. **The second-window branch takes the wrong path.** With the container set at the first realize, `existing` is
   never NULL again. A second window with a menu would take the "already ours" path, and its menu would be lost.
   The states must be explicit, and "filled" means `n_items > 0`.
2. **The candidate filter misses dialogs inside the window.** libadwaita 1.8 presents an `AdwDialog` inside the
   window's child (`adw-application-window.c:253-259`), so a dialog's MenuButton, or a list row's menu button, has
   the main window as its root. Late finds must be limited to the titlebar, or to a GtkHeaderBar/AdwHeaderBar
   ancestor, with no AdwDialog/GtkPopover ancestor.
3. **The emission hook must not be removed from inside itself.** Measured on GLib 2.88.0: doing so gives
   `G_HOOK_IN_CALL` criticals and leaves the hook list corrupt.

**Recommended:**
- Override the `map` vfunc of GtkMenuButtonClass and GtkPopoverMenuBarClass instead of adding an emission hook.
  The classes are private, so there are no subclasses.
- Handle unrealize and destroy, since a weak reference fires only at finalize, which is late under .NET.
- Hold strong references on our menus, and make an application's takeover permanent.
- Skip our own container. GTK can build an in-window PopoverMenuBar holding it, which
  `gtkapplicationwindow.c:218-269` shows.
- Fixes to the RESOLVE list, and test-plan additions: `G_DEBUG=fatal-criticals`, and a real GDBusMenuModel client
  subscribed to the empty container.

**Answers to the four questions:**
1. Waiting for the window's life is acceptable with the narrowed late-find filter.
2. Only GtkApplicationWindow should wait.
3. `items-changed` should be a separate step, because rebuilding with remove-all plus appends sends N+1 `Changed`
   signals and collapses an open menu.
4. No menubar-shaped placement in 0.11.

## Design review round 2 (Design Challenger, 2026-10-13): REVISE

The design is in DESIGN.md (round 2 at `5ba5d45`).

**Resolved:** the round-1 blocking findings, in principle. The `map` shim is the right mechanism: `map` is a
class-offset signal (`gtkwidget.c:1742-1746`), GtkMenuButton does not override it, and Pinta's buttons map through
`gtk_widget_set_parent`. gtk-nocsd 0b77e1b patches no GtkMenuButton vfunc, and "score > 0" is safe for Pinta.

**Blocking:**
1. **`g_type_class_peek` would install no shim in Pinta.** Its first GtkMenuButton is created after `Present()`,
   so the class is not initialised yet.
2. **The Adw types must be looked up at each late look.** libadwaita is loaded after GTK in GI and .NET
   applications, so a lookup at hook time returns 0. AdwHeaderBar would then never match, and Pinta would be
   rejected.

**Non-blocking:**
- the in-window empty bar exists when `gtk-shell-shows-menubar` is FALSE;
- no fill with 0 items;
- check `set_menubar`'s preconditions first;
- runtime subclasses of GtkMenuButton;
- one record per GtkApplication;
- filter before `add_candidate`, and require `shown`;
- re-entrancy during the fill;
- Pinta's small ranking margin;
- titlebars under gtk-nocsd;
- test hooks through the debug log;
- the Adw tests are required, but neither the builder nor `debian/control` has libadwaita headers.

## Design review round 3 (Design Challenger, 2026-10-13): APPROVE

**Checked against GTK 4.22.4 and GLib 2.88.0:**
- All the round-1 and round-2 blocking findings are answered.
- `g_type_class_ref` is correct, and neither GtkMenuButton nor GtkPopoverMenuBar overrides `map`.
- A non-zero Adw type lookup is guaranteed whenever such a widget exists.
- Patching subclasses is safe, and Pinta's own `ToolBarDropDownButton : Gtk.MenuButton` makes that path real.
- No fill with 0 items cannot busy-loop.
- `debian/control` really is unchanged: no test runs at build time today either.

The non-blocking points are requirements for the code, listed at the end of DESIGN.md.

## The implementation: unity-gtk4-menu 0.12 (2026-10-13)

Version: UNITY-20261013-013 became 0.11 (the PyGObject fix) and was published first. This task is 0.12, rebased
onto the published 0.11 (`00fabde`). Following later menu changes (`items-changed`: Nautilus, Papers, Console)
stays out of it: UNITY-20261013-008, for 0.13.

Commits on unity-gtk4-menu `b/UNITY-20261012-004`:
- `1e672ae` Give a menu that appears after realize to the global menu. This is the code of the round-3 design. It
  is unchanged by the rebase; the diff against the commit before the rebase is the 0.11 hunk under it.
- `02fb9ab` Release 0.12.
- `83e244f` and `beabb57` the tests (case 10 dropped: GTK refuses an application window before the application's
  startup, so the "not registered" check is defensive only).
- `569366d` README: the libgtk-4 fallback of 0.11 (UNITY-20261013-017).
- `910f912` the test fix (below).

Build: `build-0.12/`, sbuild resolute, PASS, `source_commit` 910f912. The library deb is byte-identical to the
build of 569366d (sha256 `1e5d6040…`), on which the first runs were made: the test fix changes only `tests/`.

### The test fix

On 0.12 the first run failed cases 1, 2 and 9. The library's log said "menubar filled late" each time. Measured with
debug copies of the test (scratchpad):
- **Timing.** The library fills the menubar about 20 ms after the late widget's map, in 10 of 10 runs. But the
  map itself comes 0.5-0.8 s after packing under Xvfb. With the library preloaded alone, the widget maps at once,
  inside a frame that takes 0.3 s. A fixed 500 ms wait fits neither case. The cases now wait for the map and then
  for the filled holder, up to 3 s each.
- **The D-Bus client.** `client_items()` dropped the holder's submenu proxy right after asking for its items.
  That ends the GDBusMenuModel subscription before the reply arrives. With the proxy held, a client subscribed
  before the fill sees the late menu. The test now keeps it while waiting.

### Target tests (target2: Clean-2 → live, then the 0.12 deb; logs/05-15)

| test | log | result |
|---|---|---|
| latetest + latetest-adw against 0.11 (base-red) | 05 | 6 fail as expected: 1, 2, 4, 9, 11, 6a, each with "the late … is not in the menubar"; 3, 5, 7, 8, 12, 6 pass |
| the same against 0.12, session order (menu:nocsd) | 06 | 12 of 12 pass, with the library's log lines |
| the same against 0.12 preloaded alone (the gtk-nocsd opt-out) | 07 | 12 of 12 pass, the Adw cases included |
| Pinta 3.1.2, header-bar layout, cold session | 09 | the empty menubar is set at realize; the late look ran 4.7 s after the window mapped, on the map of its header-bar buttons; it chose the main menu (39 labels, `_File` … `_Help` under the "Pinta" holder); the panel shows the "Pinta" entry; Alt+F10 opens the panel popup and Escape closes it (popwatch); the HUD returns Pinta's commands ("Save As… (Pinta, File)") |
| the UNITY-20261012-003 set, debug log | 10 | Text Editor and Calculator: the menu is found at realize, no wait, no late look, and the map shims are never installed; mnemo.py: its own menubar, untouched; gnome-tour (no menu): its window waits, no look, no fill |
| the same set by events | 11-13 | Calculator (Alt+F10), Text Editor (Alt+F10) and mnemo.py (Alt+F) open their panel popup, and Escape closes it. Calculator's first attempt went to the Accessibility indicator: the Calculator window was not the active one. The retry with the window activated opened its menu |
| cost: 10 000 map/unmap cycles of a menu button in an application window without a menu | 14 | per cycle, 5 runs each: no preload 5.1-8.2 µs, 0.11 + gtk-nocsd 6.9-11.2 µs, 0.12 + gtk-nocsd 7.4-8.5 µs (medians 7.48 and 7.75); the shim's cost is within the spread |
| shim calls (bpftrace by name, on the shipped file joined with its dbgsym, same `.text`) | 15 | maptest: 10 001 calls of the button shim, 3 looks (2 idle looks) for 10 000 maps; Pinta, 20 s from start: 6 button-shim calls (1.1 ms with the probes' overhead), 2 looks (6.4 ms), 1 idle look, 1 late fill |

An application window without a menu (gnome-tour) waits without any panel entry. Its window has
`_GTK_MENUBAR_OBJECT_PATH` for the empty menubar, but the panel lists no entry for it (`sync.sh`, measured in the
same session). Its wait ends in one of these ways, with no timer:
- a late look fills the menubar, which drops every waiting window of that application (`look()` →
  `waiters_drop_record`);
- the application sets a menubar of its own (`go_taken`);
- the window is unrealized or destroyed (`on_window_gone`);
- a scheduled look finds the window already gone (`look_idle`).

Notes on the cost runs:
- bpftrace does not place probes by offset in the stripped library ("Could not resolve address"). The by-name
  probes therefore ran on the shipped file joined with its dbgsym by `eu-unstrip`; its `.text` is identical.
- Under the probes the maptest loop takes 132 µs per cycle, so the time inside the shims there is the probes'
  overhead. The cost is the wall-clock comparison of 0.11 and 0.12 above.
- In the second probe run, bpftrace printed no counters for Pinta, and the late-look count (2) also includes the
  first run, because the log was not removed in between. Pinta's numbers are from the first run.
