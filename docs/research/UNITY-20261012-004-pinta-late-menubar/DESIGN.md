# UNITY-20261012-004 design: unity-gtk4-menu 0.11, menus that appear after realize (variant A)

Agent B, 2026-10-13. For the Design Challenger, round 1. No code exists. May chose variant A (README, "Variants"):
event-driven, no timer.

Base: unity-gtk4-menu 0.10 (`aa00846`, branch `a/UNITY-20261012-006`). Its `src/` is the same as 0.9 (`7ce9092`);
the line numbers below are 0.9's.

## The problem in one paragraph

`attach_menubar()` (:900-950) runs once per window, from the realize hooks (:956-971). It looks for a
`GtkMenuButton` or `GtkPopoverMenuBar` model in the window (`find_menu_model`, :435), and if it finds one it sets a
holder menubar with `gtk_application_set_menubar`. If it finds none, it returns ("no menu model in this window"),
and nothing ever looks again. GTK writes `_GTK_MENUBAR_OBJECT_PATH` only at realize, and only if a menubar is set at
that moment (gtk 4.22.4 `gtkapplication-x11.c:41-65`). Pinta 3.1.2 realizes its window (`Present()`) and only then
packs its header-bar MenuButtons, so it has no global menu (logs/02 p1).

## Mechanism

### 1. The menubar exists from the first realize

The menubar becomes two GMenus kept for the application's life:

- **`container`**, the menubar itself. It is set with `gtk_application_set_menubar` at the first realize, if the
  application has no menubar of its own (the existing check, :908). At first it has **0 items**. GTK then writes
  `_GTK_MENUBAR_OBJECT_PATH` on every window realized from now on, the first one included, since we act before
  chaining up (:956-971 order unchanged).
- **`inner`**, the holder's submenu. When a menu is found, `container` gets one item: the existing holder,
  labelled with the application's name (`menu_label`, :468), with `inner` as its submenu. `inner` holds the
  cleaned copy (`clean_model`, :851).

Every later change edits these two GMenus in place: `g_menu_remove_all(inner)` and appending. GTK keeps one
exporter, so the panel's subscription stays valid and gets `org.gtk.Menus.Changed`. Replacing the model would leave
current subscribers with nothing (glib 2.88 `gmenuexporter.c:265`, :710). That is why it is not done.

A window found with a menu at realize (every application that works today) takes exactly today's path, except that
the holder now goes into `container` instead of being the whole menubar. The model the panel sees is the same: one
holder item with the cleaned copy as its submenu.

### 2. Windows that are still waiting

A window whose realize finds no menu is put on a **waiting list** if it is a candidate:

- **The window is a `GtkApplicationWindow`, or a `GtkWindow` with an application.** A window without an
  application is not a candidate, as today (:904).
- **It has no transient parent** (`gtk_window_get_transient_for == NULL`) and is not modal. This keeps dialogs out.
  A file chooser or a preferences dialog has its own MenuButtons, and one mapped later must not become the
  application's menubar. Today this risk exists only at realize time.
- **The application's `container` is still empty.**

**The list holds windows by weak reference** (`g_object_weak_ref`). A window leaves the list when the first of these
happens:
- **(a) A menu was found** for it, so `container` is filled.
- **(b) `container` was filled from another window** of the same application. Since the menubar is per
  application, once it is filled every window leaves the list: they get stand-ins as today (:921-928).
- **(c) The window is unrealized or finalized**, through the weak reference.
- **(d) The application set a menubar of its own**, see 5.

Nothing else ends the wait: no timer, no count. A window of an application that never builds a menu waits for its
whole life. Point 4 bounds what that costs.

### 3. Events that trigger a look

**A `GtkWidget::map` emission hook.**
- **When it exists:** it is installed when the waiting list goes from empty to non-empty, with
  `g_signal_add_emission_hook(g_signal_lookup("map", GTK_TYPE_WIDGET), 0, …)`. It is removed
  (`g_signal_remove_emission_hook`) when the list becomes empty again.
- **Applications that never use it:** an application whose menu is found at realize (Text Editor, Calculator, and
  every other one that works today) never installs it.
- **What it does,** in order:
  1. returns TRUE at once unless the instance is a `GtkMenuButton` or a `GtkPopoverMenuBar`, which is two
     `g_type_check_instance_is_a` calls;
  2. takes `gtk_widget_get_root()`;
  3. returns TRUE unless the root is on the waiting list;
  4. otherwise schedules a **look** for that window: one `g_idle_add` per window, coalesced, so Pinta's five buttons
     produce one look.
- **Why `map` works:** it is not `G_SIGNAL_NO_HOOKS` (gtkwidget.c:1743). `GObject::notify` is (gobject.c:1083), so
  notify cannot be hooked class-wide.
- **Why it catches Pinta:** `adw_header_bar_pack_end` → `gtk_box_prepend` maps a visible child of a mapped parent
  synchronously (gtkwidget.c:6336-6342). The model is already set when the button is constructed
  (`new Gtk.MenuButton { MenuModel = … }`).

**Per-instance `notify` for buttons mapped without a menu.**
- During a look, a mapped `GtkMenuButton` in a waiting window that has neither a menu model nor a `GtkPopoverMenu`
  popover gets `notify::menu-model` and `notify::popover` connected. A `GtkPopoverMenu` popover gets
  `notify::menu-model`, and so does a `GtkPopoverMenuBar` without a model.
- They use `g_signal_connect_object` with the window as the gobject, so they go away with the window.
- Each schedules a look, and they are disconnected when the window leaves the list.

**Setters are not interposed.** GTK links with `-Bsymbolic`, so its own property-to-setter calls never go through the
PLT, and .NET resolves its calls through `dlsym` on libgtk's handle. Interposing would miss Pinta.

### 4. The look

A look is the existing `find_menu_model()`, `clean_model()` and stand-ins, applied to a waiting window from an idle
callback. If it finds a menu, `inner` is filled and the holder item goes into `container`. All windows leave the
list, and the `map` hook is removed when the list is empty.

### 5. Following the source menu (`items-changed`)

`clean_model` copies; the copy is static (comment at :838-840). After a fill, `items-changed` is connected on the
source model and on every section and submenu, to depth 16, as `reachable_items` walks them. Any signal schedules
one idle rebuild: `clean_model` again into `inner`, through `g_menu_remove_all` and appending. The connections
are dropped and re-made on each rebuild, since the submenus may be new objects, and held weakly against the
source.

- **Why it is in 0.11:** May's variant A names it, and without it a filled-late menu could be stale from the
  start. Pinta fills its submenus while it registers actions, at Startup, before the window exists, so that case
  is unlikely.
- **Side effect:** it also fixes the "menu changes later" cases (Nautilus' Undo relabel; the -034 survey).
- **Not in 0.11:** following a *different* button being shown later (Papers, Console). gtk-nocsd's `a450853` does
  that with its `map` hook's refind, and it is a separate behaviour change.

### 6. An application that sets its own menubar later

- **At realize:** "already has a menubar", unchanged.
- **Later:** if `gtk_application_get_menubar(app)` is no longer our `container`, we stop. Every window leaves the
  list, the `map` hook goes, the `items-changed` connections go, and our objects are released. We never set ours
  back over theirs. We notice this through a per-instance `notify::menubar` on the GtkApplication
  (`g_signal_connect_object`) and at every look.
- **The remaining risk:** GTK re-exports at the same path, `<app path>/menus/menubar` (gtkapplication-dbus.c:492),
  but the panel's existing subscription to the old export gets no `Changed`. Whether unity-panel-service then
  shows the application's menu, or nothing until the window is focused again, is not known; it is to be measured
  (tests, case 5). Today such an application has no global menu at all, because the property is missing.

### 7. The empty `container`

- **Panel:** for a window that never gets a menu, the panel shows nothing. That was measured with gtk-nocsd's
  equivalent (research/nocsd-gaps, gnome-tour), and GTK shows no in-window bar for 0 items
  (gtkapplicationwindow.c:218).
- **HUD:** what it shows for an empty menubar is not known; to be measured (tests, case 3).
- **Applications that read their own menubar:** `gtk_application_get_menubar()` now returns our empty
  `container` for applications without a menu. Today it returns NULL. An application that reads it and acts on
  non-NULL is a risk. No such application is known; measured in the regression run (tests, 9).

## Cost of the `map` hook

- **When it costs nothing:** while no window waits, the hook does not exist. That is the case for every
  application whose menu is found at realize, and for every process without GTK4 (the RTLD_NOLOAD check, :1043).
- **When it does cost:** for a waiting window, each `map` emission of any widget in the process runs two
  type-instance checks.
- **To measure** before APPROVE, with a scratchpad prototype, no package code:
  - the number of hook calls and their total time, through a debug counter logged with `note()`;
  - in Pinta from start to idle;
  - in an application without a menu that keeps waiting, for its life (gnome-tour, or a test window that maps and
    unmaps 10 000 buttons);
  - in Nautilus browsing a large directory, if it ever waits.
- **Expected:** well under 1% of the map cost, since `map` itself runs layout and CSS. This is to be shown, not
  assumed.

## Tests

**In `tests/`,** a C test like `tests/classtest.c`, run under `xvfb-run` with `UNITY_GTK4_MENU_FORCE=1`. Each case
checks `_GTK_MENUBAR_OBJECT_PATH` on the window, `gtk_application_get_menubar()`, and the exported items over
`org.gtk.Menus`:

1. A MenuButton packed after `gtk_window_present()`, Pinta's order: the menu appears in `container` without a
   timer.
2. A `GtkPopoverMenuBar` added after present.
3. A window with no menu: `container` stays empty. The waiting list is emptied and the hook removed when the window
   is destroyed. Also: the HUD and the panel with it, on target.
4. A MenuButton mapped without a model and given one later (`gtk_menu_button_set_menu_model` after map): the
   per-instance notify fills the menu.
5. The application sets its own menubar after realize: ours is released and not set back. The application's menu
   is what the panel shows, measured on target.
6. A transient dialog with a MenuButton, opened while the main window waits: it does not become the menubar.
7. `items-changed`: an item is added to the source after the fill, and the exported copy follows.
8. The existing realize path is unchanged: a menu found at realize gives the same exported model as 0.10
   (`tests/gjstest.js` and classtest).

**On target2** (Clean-2 → live → install the build):

9. Pinta 3.1.2 in header-bar mode: File … Help under the holder on the panel, with Alt+F10 and the HUD. Then the
   regression set from UNITY-20261012-003: Text Editor, Calculator, mnemo.py, judged by events.
10. Nautilus' Undo relabel after a rename (items-changed).

## Packaging

- **Version:** unity-gtk4-menu 0.11.
- **`debian/control`:** unchanged; no new dependency. GLib and GTK are already resolved at run time through
  `dlsym`.
- **New symbols** go through `RESOLVE`, which does nothing if one is missing:
  - `g_signal_lookup`, `g_signal_add_emission_hook`, `g_signal_remove_emission_hook`;
  - `g_idle_add`, `g_source_remove`;
  - `g_menu_remove_all`;
  - `g_object_weak_ref`, `g_object_weak_unref`;
  - `g_signal_handler_disconnect`, `g_signal_handlers_disconnect_matched`;
  - `gtk_widget_get_root`, `gtk_window_get_transient_for`, `gtk_window_get_modal`;
  - `gtk_widget_get_mapped`.
- **Size estimate:** 150-200 lines in `src/unity-gtk4-menu.c`, plus the test.
- **Not changed:** the environment.d file, the gsettings schema, the label logic.

## Questions for the Challenger

1. Is "a waiting window waits for its life, and the hook exists only while some window waits" bounded enough, or
   should a window also leave the list at its first unmap?
2. Is the candidate filter (no transient parent, not modal) right? Should plain `GtkWindow`s with an application be
   candidates at all, or only `GtkApplicationWindow`?
3. Should `items-changed` following be in this release, or be a separate step after the late-menu fix?
4. Placing a menubar-shaped menu (all top-level items submenus, as Pinta's) on the panel without the holder, as
   gtk-nocsd does: proposed **not** in 0.11, because it changes how existing applications look. Agreed?
