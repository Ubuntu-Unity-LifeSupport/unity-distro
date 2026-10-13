# UNITY-20261013-008 design: unity-gtk4-menu 0.13, follow changes of the menu found

Agent B, 2026-10-13. Round 1, for the Design Challenger. No code exists.

**Scope (C, 2026-10-13).**
- In scope: the items of the **same** model change after the first export (Nautilus's Undo relabel, README
  "Measurement").
- Not in scope:
  - a different menu that shows later (Papers' document menu, UNITY-20261013-028, likely 0.14);
  - a menubar the application sets after realize (UNITY-20261013-024, weighed at the end).

**Constraints (C, carried from UNITY-20261012-004 round 3).**
- The one holder item is replaced in place: no `remove_all` storm.
- Unchanged copies are skipped.
- An open panel menu must not collapse while `items-changed` fires.

**Base:** unity-gtk4-menu 0.12 (`4b7a537`). Line numbers are 0.12's `src/unity-gtk4-menu.c`.

## What 0.12 does

- `look()` (:1208) finds the menu (`find_menu_model`) and copies it with `clean_model()` (:1002):
  - a new `GMenu` per level;
  - `custom` items dropped;
  - each item's actions given stand-ins where needed (`proxy_item` → `proxy_for`, which only adds a missing
    action, :878);
  - sections and submenus copied recursively, depth 16; an item whose link cleans to nothing is dropped.
- It appends the copy's items to `rec->inner` and one holder item (`menu_label`, submenu `inner`) to
  `rec->container`.
- `container` and `inner` live as long as the record and are never replaced (:1058-1062).
- The source model is not kept, and nothing watches it. So a change in the application's menu never reaches the
  copy (Nautilus).

## The change

### 1. Keep the source and watch it

- The record keeps, after a fill:
  - `rec->source`, a reference to the model the copy was made from;
  - `rec->owner`, a weak pointer to the widget it came from;
  - `rec->window`, a weak pointer to the window that filled it. Its action map gets the stand-ins.
- `watch()` connects `items-changed` on `source` and on every section and submenu model reachable from it, to the
  depth `clean_model` copies (16).
- The handlers and a reference to each model are kept in one list on the record, so they can be disconnected
  exactly.

### 2. One rebuild per burst

- Every `items-changed` of a watched model only schedules **one idle** per record (`rec->rebuild_idle`).
  Further signals before it runs add nothing.
- The idle does the following:
  1. **Drops** every watch (`unwatch()`), because a change can replace any section or submenu object.
  2. **Copies** `source` again with `clean_model`, in the same scope (`owner`, the window's action map). If the
     window is gone, the scope's map is NULL, as for a non-application window today.
  3. **Applies** the new copy to `inner` (3.), then watches the source again.
- No timer: the idle runs once per main-loop turn at the most. A model changed on every frame (none is known)
  would cost one rebuild per turn; see question 3.

### 3. Apply the new copy in place, at the deepest level that changed

`sync(GMenu *ours, GMenuModel *new)` walks the two menus position by position:
- **Same item.** Same attributes (label, action, target, icon, accel and every other attribute, compared as
  GVariants) and the same link kinds:
  - the item is kept;
  - for each link, `sync()` recurses into our own copy's linked `GMenu`. Our copy is always a `GMenu` made by
    `clean_model`, so it can be edited.
- **Different item:** it is replaced at that position. One `g_menu_remove()` and one `g_menu_insert_item()`
  happen at that index, the only `items-changed` pair for it.
- **Extra positions:** removed from the end of ours or appended from the new copy.

So:
- **Nothing changed:** no `items-changed` on our side at all. This is the "skip unchanged copies" requirement. A
  burst that changes and then restores a label emits nothing.
- **Nautilus's relabel:** only the Undo item in its section of `inner` is replaced. `container`, the holder and
  `inner` keep their identity, and so do the other sections.
- **An open menu on the panel:** the menu shown (`inner` or a deeper submenu) is never replaced unless its own
  item changed. The panel's subscription to that group stays. Whether the panel's open popup survives an item
  replaced inside it is measured on target (test 4); that is the constraint's real check.
- **Holder label:** the holder is never touched. The application's name does not change.

### 4. When watching stops

- **TAKEN** (`go_taken`): unwatch, drop the idle, release `source`.
- **The record freed** (the application finalized): the same, in `record_free`. The handlers die with the models
  anyway, but they are disconnected first so that no handler runs with a freed record.
- **The source's owner widget is destroyed:** the copy stays as it is, and the source reference keeps the model
  valid, so a late signal still finds a model. Following a *different* model is UNITY-20261013-028.

### 5. Stand-ins

- The rebuild runs `proxy_item` again for the filling window. New actions in changed items get their stand-ins;
  existing ones are found and kept (`proxy_for` :878).
- Other application windows got their stand-ins at their own realize (:1475-1495). The rebuild repeats that for
  each `GtkApplicationWindow` of the application (`gtk_application_get_windows`), with a copy made only for its
  stand-ins, as at realize.
- A stand-in whose item is gone stays in the window's action map, unreachable from the menu. It is harmless,
  and 0.12 never removes one either.

### New symbols through RESOLVE

- `g_signal_connect_data` and `g_signal_handler_disconnect` (already resolved);
- `g_menu_remove`, `g_menu_insert_item`;
- `g_menu_model_iterate_item_attributes` with `g_menu_attribute_iter_get_next`, for the attribute comparison;
- `g_variant_equal`;
- `gtk_application_get_windows`.

Fail-closed as today.

## Tests

1. **latetest case 13 (Xvfb).** An application window with a menu at realize. A section item is relabelled, then
   another item added, then the change undone. Checks:
   - the application's menubar and a subscribed `GDBusMenuModel` client see each state;
   - `container`, the holder and `inner` are the same objects;
   - the `items-changed` emissions on `inner`, counted by the test, are exactly 2 for the relabel (one remove, one
     insert at that position) and 0 for a change that restores the previous state within one burst;
   - the log has the new "menu changed; N item(s) replaced" line.
2. **latetest case 14:** a burst of 100 changes in one main-loop turn gives one rebuild (log) and at most one
   replaced item per changed position.
3. **latetest case 15:** TAKEN after a fill stops the watch. A later `items-changed` on the old source rebuilds
   nothing (log), and no handler runs after the application is finalized (G_DEBUG=fatal-criticals, valgrind
   optional).
4. **target2, Nautilus.** A rename, through `research/nocsd-gaps/tests/naut.sh` over D-Bus and by keys, makes the
   export show "Отменить переименование", judged by `menudump.py`. Then the HUD returns it for "переим".
5. **target2, an open panel menu.** A small test application relabels one item of its menu every 2 s. The
   holder is opened with Alt+F10 and left open for 10 s. Judged by events:
   - the popup stays mapped (popwatch.sh);
   - the panel's entry keeps its id (Sync);
   - after Escape and Alt+F10 again, the label is the latest one.
6. **Regression.** latetest 1-12 (both preload forms); order-0.9.sh unchanged; Pinta (filled late, then its menu
   follows its own changes, e.g. Undo enabled after a stroke); the UNITY-20261012-003 set by events.
7. **Control.** Cases 13-15 and target tests 4-5 against 0.12, which must fail 13 and 4 (stale) and show no
   rebuild.

## Questions for the Challenger

1. Is the deepest-level in-place `sync()` right, against the simpler "replace the changed top-level item of
   `inner`"? The simpler form replaces a whole section when one label in it changes.
2. Attribute comparison: compare all attributes, or label, action, target and accel only? Icons are
   GVariant-serialised GIcons and compare fine with `g_variant_equal`.
3. Is an idle per burst enough, or should a rebuild be rate-limited (it would need a timer)? I know of no
   application that changes its menu continuously.
4. The other windows' stand-ins: repeat them on every rebuild (my proposal), or only when a new action appears?

## UNITY-20261013-024 (a menubar the application sets after realize), weighed

The idea is "put the application's menubar into our container" instead of releasing ours.
- **What GTK does.** When the application sets its menubar, GTK unexports ours and exports the application's at
  the same path (UNITY-20261013-023).
- **What keeping ours would take.** Ours would have to stay exported, so we would have to set our container back
  as the application's menubar.
  - The application's own `gtk_application_get_menubar()` would then return our container, not its model.
  - That changes the application's view of itself, for example GtkApplicationWindow's in-window menubar when the
    shell shows none.
- **The other route.** Making the panel subscribe again belongs to unity.

So it is not a cheap extension of `sync()` and is left out of 0.13. The survey (logs/02) decides whether
UNITY-20261013-024 stays BACKLOG.
