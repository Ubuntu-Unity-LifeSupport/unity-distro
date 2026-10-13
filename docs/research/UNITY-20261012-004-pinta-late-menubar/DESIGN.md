# UNITY-20261012-004 design: unity-gtk4-menu 0.11, menus that appear after realize (variant A)

Agent B, 2026-10-13. **Round 2**, for the Design Challenger. Round 1 (`92666f6`) was REVISE; its findings are in
README.md, "Design review round 1", and the table at the end says where each one is answered. No code exists.

**Scope** (May's decision through C): 0.11 covers late menus only, which is Pinta's case. "An empty menu at
realize, filled when the menu button appears." Following later changes of a menu (`items-changed`: Nautilus,
Papers, Console) is UNITY-20261013-008, for 0.12.

**Base:** unity-gtk4-menu 0.10 (`aa00846`). Its `src/` is the same as 0.9's (`7ce9092`), and line numbers are 0.9's.

## The problem in one paragraph

`attach_menubar()` (:900-950) runs once per window, from the realize hooks (:956-971). If no `GtkMenuButton` or
`GtkPopoverMenuBar` model is in the window at that moment, it gives up for good. GTK writes
`_GTK_MENUBAR_OBJECT_PATH` only at realize, and only with a menubar already set (gtk 4.22.4
`gtkapplication-x11.c:41-65`). Pinta 3.1.2 realizes its window (`Present()`) before it packs its header-bar
MenuButtons, so it has no global menu (logs/02 p1).

## States

The library keeps one record for the application it runs in. A process has one GtkApplication with windows; a
second GtkApplication in the same process is ignored, as 0.10 ignores it. The record is in one of four states:

| state | meaning | `container` | `inner` |
|---|---|---|---|
| `NONE` | nothing set yet; the application has no menubar | - | - |
| `OURS_EMPTY` | our menubar is set, no menu found yet | ours, 0 items | ours, empty, not linked |
| `OURS_FILLED` | our menubar holds the holder item | ours, 1 item (the holder) | ours, the cleaned copy, linked from the holder |
| `TAKEN` | the application set a menubar of its own | released | released |

- **`container` is the menubar.** `gtk_application_set_menubar(app, container)` is called exactly once, at the
  first realize in `NONE`.
- **The holder** is the existing single item labelled with the application's name (`menu_label`, :468), whose
  submenu is `inner`. `inner` holds the cleaned copy (`clean_model`, :851).
- **Strong references:** we hold strong references on `container` and `inner` from creation until `TAKEN` or the
  end of the process. 0.10's borrowed `our_menubar` pointer (:945) goes, so a stale address can never be confused
  with the application's menubar.
- **`TAKEN` is final:** a later `gtk_application_set_menubar(app, NULL)` by the application does not bring us back.

### Transitions

**At every realize of a window with an application** (the hook, before chaining up, as today):

- **`NONE`:**
  - If `gtk_application_get_menubar(app)` is non-NULL, go to `TAKEN`. The application set its own, which is
    today's "already has a menubar".
  - Otherwise create `container` and `inner`, set `container`, and go to `OURS_EMPTY`. GTK then writes the
    property for this window and every later one.
  - Then, as for `OURS_EMPTY`, look in this window.
- **`OURS_EMPTY`:** run today's `find_menu_model` on this window, with today's realize-time rules. If a menu is
  found, fill (below) and go to `OURS_FILLED`. If not, and the window is a `GtkApplicationWindow`, put it on the
  waiting list.
- **`OURS_FILLED`:** this is today's second-window case. Clean this window's own menu and keep only its stand-ins
  (:921-928). Nothing is waited for.
- **`TAKEN`:** do nothing.

**Fill:** clean the found model into `inner` (append into the empty `inner`), then append the holder item, with
`inner` as its submenu, to the empty `container`. That is one `items-changed` on `container` after `inner` is
complete, so a panel subscribed to the empty `container` sees one change, from 0 items to the holder. Every waiting
window then leaves the list.

**Round-1 blocking 1:** the gnome-contacts order (a setup window without a menu, then the main window with one) now
works. The setup window puts the record in `OURS_EMPTY` and does not wait, because it is a plain `GtkWindow`; if it
were an application window it would wait. The main window's realize finds its menu and fills. 0.10 ends the same
way; 0.11 additionally keeps the property on the setup window.

**`TAKEN` from `OURS_*`:** a per-instance `notify::menubar` on the GtkApplication, connected when we enter
`OURS_EMPTY` (`g_signal_connect_object`; the signal fires synchronously on change, `gtkapplication.c:1024-1028`),
sees that `gtk_application_get_menubar(app)` is no longer `container`. GTK has already unexported ours at that point,
so it is safe to clear the waiting list, drop the window handlers and release `container` and `inner`.

## Waiting windows and late finds

### Who waits

**Only a `GtkApplicationWindow` waits,** in `OURS_EMPTY`, when its realize found no menu. A plain `GtkWindow` with
an application is still looked at during its realize, as today, but does not wait. Round-1 Q2.

**A window leaves the list when the first of these happens:**
- (a) the application is filled, from this window or another;
- (b) the window is unrealized or destroyed: per-instance `unrealize` and `destroy` handlers, because a weak
  reference fires only at finalize, and under .NET that waits for the garbage collector (round-1 #5);
- (c) `TAKEN`.

A weak reference stays only as a safety net. A window that is realized again after an unrealize goes through realize
again like any window. Nothing else ends the wait: no timer, no count. Round-1 Q1: waiting for the window's life is
acceptable with the narrowed late-find filter below.

### The trigger: the `map` vfunc of the two menu widgets

When the first window starts waiting, we replace `map` in the classes `GtkMenuButtonClass` and
`GtkPopoverMenuBarClass` with a shim. It is the same technique as the existing realize hook (`hook_class`, :1017),
and it is installed once. These classes are private (`gtkmenubutton.c:140`, `gtkpopovermenubar.c:98`), so there are
no subclasses to miss. Doing it then, not at load, keeps the classes from being initialised early (:1139-1146).

**The shim:**
1. chains up to the real `map` first;
2. returns at once if the waiting list is empty, which is one integer test;
3. takes `gtk_widget_get_root()`, which is O(1): a cached pointer (`gtkwidget.c:6432`);
4. if the root is a waiting window, schedules one **late look** for it: one `g_idle_add` per window, kept in the
   window's entry and coalesced. Pinta's five buttons give one look.

**Why this design avoids the old problems:**
- No emission hook is added or removed, so round-1 blocking 3 does not arise.
- Other widgets pay nothing, and these two pay only while a window waits (round-1 #4).
- Pinta is caught: `adw_header_bar_pack_end` → `gtk_box_prepend` maps a visible child of a mapped parent
  synchronously (`gtkwidget.c:6336-6342`), with the button's model already set.

**Per-instance notify, for a button mapped without a menu.** During a late look, a candidate button (filter below)
that has neither a menu model nor a `GtkPopoverMenu` popover gets `notify::menu-model` and `notify::popover`. A
`GtkPopoverMenu` popover gets `notify::menu-model`.
- They are connected with `g_signal_connect_object` to the window, and the button is marked with
  `g_object_set_data`, so a second look does not connect it again (round-1 #9).
- The handler only schedules a look if the window is still waiting. It is not disconnected explicitly; the
  connection ends with the window.

### What a late look accepts

A late look is `find_menu_model` on the waiting window, with a narrower filter than at realize (round-1 blocking 2).

**An owner is accepted only if:**
- it is in the window's titlebar (`gtk_window_get_titlebar` subtree), **or** it has a `GtkHeaderBar` or
  `AdwHeaderBar` ancestor below the window;
- **and** it has no `AdwDialog`, `GtkPopover` or `AdwBottomSheet` ancestor.

Adw types are looked up with `g_type_from_name`, which returns 0 when libadwaita is not loaded; a 0 type matches
nothing.

**Also skipped:**
- a candidate whose model is `container` or `inner`, or a `GtkPopoverMenuBar` whose parent is the window itself. GTK
  builds such a bar with our menubar when `show-menubar` is TRUE and `gtk-shell-shows-menubar` is FALSE, for example
  under Xvfb without XSettings (`gtkapplicationwindow.c:218-269`; round-1 #7).

**The ranking is unchanged:** shown, then primary, then the most reachable app./win. items. A late look also needs a
score above 0, so a menu that reaches no application or window action does not become the application menu.

**Pinta passes:**
- its buttons are in an `Adw.HeaderBar` (`WindowShell.cs`), and none is in a dialog;
- "Main Menu" has the most app. items (`app.new`, `app.open`, … under File and Edit);
- the Effects, Adjustments, Image and View buttons score lower.

That ranking is to be confirmed on target (tests, 9).

**C's question: Text Editor and Calculator have a ⋮ menu in the header bar.** Their menu is found at their first
realize (UNITY-20261012-003 logs: the panel shows "Текстовый редактор" and "Калькулятор" at once). The record goes
from `NONE` straight to `OURS_FILLED`: nothing waits, the `map` shim is never installed, and no late look ever
runs. Later menu buttons in these applications, such as a dialog's, a row's or another header-bar button, are
ignored, exactly as in 0.10. The late path exists only for an application whose menubar is still empty. Tests 8 and
9 check this on target.

### The late look's fill

The same as at realize: `clean_model` into `inner`, then the holder into `container`. The record goes to
`OURS_FILLED`, the waiting list is cleared, and the shim's second test makes it return at once from then on.

## Remaining downsides, stated

- **`gtk_application_get_menubar()` is non-NULL** in `OURS_EMPTY` for applications without a menu. Today it is NULL.
  No application relying on NULL is known; tests 3 and 9 look.
- **Panel and HUD:** for an application that never gets a menu, the panel shows nothing (gnome-tour under gtk-nocsd,
  research/nocsd-gaps). The HUD with an empty menubar, and Unity's locally integrated menus (LIM), are measured in
  test 3.
- **After `TAKEN`:** the panel may keep showing our last exported items rather than the application's, because GTK
  sends no signal when it unexports. Today such an application has no property at all, and so no global menu.
  Test 5 measures which it is.
- **Stand-ins (round-1 #10):** a window that arrives in `OURS_FILLED` and whose buttons appear only after its
  realize, a second window in Pinta's order, gets no stand-ins of its own. That matters only for class actions
  (`find_class_action`), and Pinta has none; it is documented in the card. A stand-in for an item that later
  disappears stays tied to its first owner, as today (`proxy_for` :727).

## Tests

**In `tests/`:** a new C test, `tests/latetest.c`, modelled on `tests/classtest.c` and on the shelved
`research/layer-b/latetest.c`. It runs under `dbus-run-session -- xvfb-run`, with `UNITY_GTK4_MENU_FORCE=1` and
`G_DEBUG=fatal-criticals` for every case (round-1 #3, #12). Each case reads the window's
`_GTK_MENUBAR_OBJECT_PATH`, the record's state and a debug counter (shim calls, late looks), and lists the exported
items through a real `GDBusMenuModel` client.

1. **Pinta's order:** a MenuButton packed into a GtkHeaderBar after `gtk_window_present()`. The menu appears without
   a timer, and the GDBusMenuModel client, subscribed to the empty container before the fill, receives the change.
2. The same with a `GtkPopoverMenuBar` in the titlebar.
3. **No menu at all:** the state stays `OURS_EMPTY`, the window leaves the list at destroy, and the shim's counter
   stops. On target: the panel shows nothing; the HUD and LIM with it.
4. **A MenuButton mapped without a model,** given one later by `gtk_menu_button_set_menu_model`: the per-instance
   notify fills.
5. **The application sets its own menubar after realize:** `TAKEN`. Ours is released and not set back, also after
   the application sets NULL. On target: what the panel shows.
6. **A dialog in the window:** while the main window waits, an AdwDialog containing a MenuButton is presented inside
   an AdwApplicationWindow (built only if libadwaita headers are available). It does not become the menubar, and
   neither does a MenuButton in a list row or a `GtkPopover`.
7. **The gnome-contacts order:** first a plain window without a menu, then an application window with a menu at
   realize. The menu is exported; this is the round-1 blocking 1 regression.
8. **The realize path is unchanged:** a menu found at realize gives the same exported model as 0.10, and the shim is
   never installed (`tests/gjstest.js`, classtest).
9. **On target2** (Clean-2 → live → this build):
   - Pinta 3.1.2 in header-bar mode: File … Help under the holder, with Alt+F10 and the HUD, judged by events.
   - The UNITY-20261012-003 regression set (Text Editor, Calculator, mnemo.py) by events. Their ⋮ and other
     header-bar buttons have no effect, and the debug log shows no late look.
   - gnome-tour, or another application without a menu.
10. **Cost:** with a scratchpad prototype before APPROVE if the Challenger asks for it, and with the build on target
    otherwise. The shim calls and their total time in Pinta from start to idle, and in a menu-less application that
    maps and unmaps 10 000 menu buttons.

## Packaging

- **Version:** unity-gtk4-menu 0.11.
- **`debian/control`:** unchanged. The library has no NEEDED entries on GLib or GTK; everything is resolved at run
  time.
- **New symbols through `RESOLVE`:**
  - `g_idle_add`, `g_source_remove`;
  - `g_object_ref`, `g_object_weak_ref`, `g_object_weak_unref`;
  - `g_type_from_name`, `g_type_class_peek`;
  - `gtk_widget_get_root`, `gtk_window_get_titlebar` (already resolved), `gtk_widget_get_mapped`;
  - `gtk_menu_button_get_type` and `gtk_popover_menu_bar_get_type` (already resolved), `gtk_popover_get_type`,
    `gtk_header_bar_get_type`.

  RESOLVE is fail-closed: one missing symbol disables the whole library, as today. All of these exist since GTK 4.0
  and GLib 2.38 (round-1 #11).
- **Size estimate:** 130-180 lines in `src/unity-gtk4-menu.c`, plus the test.
- **Not changed:** the environment.d file, the gsettings schema, the label logic.

## Round-1 findings and where they are answered

| # | finding | here |
|---|---|---|
| 1 B | the second-window branch with a non-NULL empty menubar | States, transitions; test 7 |
| 2 B | dialogs and rows inside the window | "What a late look accepts"; only application windows wait; test 6 |
| 3 B | removing an emission hook inside itself | no emission hook: a class `map` vfunc shim; tests under fatal-criticals |
| 4 | class vfunc instead of a global hook | taken |
| 5 | weak ref fires only at finalize | `unrealize`/`destroy` handlers |
| 6 | borrowed pointer, permanent takeover | strong references, `TAKEN` final |
| 7 | the in-window bar holds our container | skip our own models and the window's own PopoverMenuBar |
| 8 | the rebuild cost | not in 0.11: UNITY-20261013-008 |
| 9 | notify bookkeeping | `g_object_set_data` mark; the handler checks waiting |
| 10 | stand-ins for late buttons in other windows | documented in "Remaining downsides" |
| 11 | RESOLVE list | updated |
| 12 | test gaps | tests 1-8 |
