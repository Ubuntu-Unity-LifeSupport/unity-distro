# UNITY-20261013-008 design: unity-gtk4-menu 0.13, follow changes of the menu found

Agent B, 2026-10-13. **Round 3**, for the Design Challenger. Rounds 1 and 2 were REVISE (README, "Design review
round 1" and "round 2"); the tables at the end say where each finding is answered. No code exists.

**Scope (C, 2026-10-13).**
- In scope: the items of the **same** model change after the first export (Nautilus's Undo relabel).
- Not in scope:
  - a different menu that shows later (Papers, UNITY-20261013-028);
  - a menubar the application sets after realize (UNITY-20261013-024, BACKLOG).

**Constraints (C).**
- The one holder item is replaced in place: no `remove_all` storm.
- Unchanged copies are skipped.
- An open panel menu must not collapse while `items-changed` fires.

**Base:** unity-gtk4-menu 0.12 (`4b7a537`). Line numbers are 0.12's `src/unity-gtk4-menu.c`.

## What 0.12 does

- `look()` (:1208) copies the menu found with `clean_model()` (:1002):
  - a new `GMenu` per level;
  - `custom` items dropped;
  - stand-ins through `proxy_item`/`proxy_for`;
  - sections and submenus recursed to depth 16, and an item whose link cleans to nothing dropped.
- It appends the copy's items to `rec->inner` and one holder to `rec->container`. Both live as long as the record.
- The source model is not kept or watched.

**What the exporter does** (GLib 2.88 `gio/gmenuexporter.c`, read by the Challenger):
- Every `items-changed` on a subscribed group sends one `Changed` at once.
- A changed position gets new links:
  - a `submenu` link always a **new group**, even for the same object;
  - a `section` link a new menu id in the parent's group.
- Untouched positions keep their ids.

So what we must not touch is exactly what an open panel menu shows.

## The change

### 1. Keep the source and watch it

- **When:** in `look()`, after a fill, so the fill at realize and the late fill share one path. The OURS_FILLED
  branch for a further window does not watch again.
- **What the record keeps:**
  - `rec->source`, a reference to the model copied;
  - `rec->owner` and `rec->window`, weak pointers: the widget the menu came from and the window that filled.
- **`watch()`:** connects `items-changed` on `source` and on every `section` and `submenu` model reachable from it,
  to the depth `clean_model` recurses (16).
  - It keeps a reference and the handler id of each model in one list on the record.
  - It **skips `rec->container` and `rec->inner`**, and any model already in the list.
  - It never watches our copy (round-1 #5).

### 2. One rebuild per burst

- A watched `items-changed` schedules at most **one idle** per record (`rec->rebuild_idle`), at
  `G_PRIORITY_DEFAULT_IDLE` (`g_idle_add`'s), so the application's own updates run first (round-2 #7).
- We watch only source models and edit only ours, so our edits cannot trigger our watch. The `syncing` flag stays
  as a cheap guard (round-1 #5, round-2 #5).
- The idle:
  1. sets `rebuild_idle = 0` and takes a reference on the application;
  2. continues only if the state is still OURS_FILLED (round-1 #6);
  3. stops following, if the weak `owner` or `window` is gone: unwatch, drop `source`, and log once "the menu's
     window or widget is gone; the menu is no longer followed". The copy stays as it is (round-1 #2).
     Following a different menu is UNITY-20261013-028;
  4. otherwise unwatches, copies `source` again with `clean_model` in the same scope, `sync()`s it into `inner`,
     watches again, and releases the reference.
- **Accepted:** a change the application makes to the source *during* the rebuild falls between unwatch and
  rewatch, and is lost until the next change. An example is a handler reacting to `proxy_for`'s
  `g_action_map_add_action`. It is rare and single-threaded (round-2 #5).
- No timer and no rate limit: one rebuild per main-loop turn at most. Every rebuild bumps a counter in the log
  line ("menu changed (rebuild N): K item(s) replaced").

### 3. `sync()`: apply the new copy in place, at the deepest level that changed

`sync(GMenu *ours, GMenuModel *new, int depth)`:
1. **Common prefix and suffix.** Equal items at the start and at the end (`same_item()`, below) are kept.
   - The suffix is bounded by `min(n_old, n_new) − prefix`, so the prefix and suffix never overlap (round-2 #2).
   - For each kept item, the links are synced by the recursion rule in 4.
   - The trim is computed before any recursion, and recursion changes no index at the level being trimmed.
2. **The middle.**
   - **Old and new middles of the same length:** they are compared item by item. An equal item is kept and
     recursed into; a different one is replaced at its position (`g_menu_remove` + `g_menu_insert_item`).
   - **Different lengths:** the old middle is removed and the new middle inserted.

   An insert or a removal therefore touches only the items in between (round-1 #1). A section that cleans to
   nothing and is dropped is a removal like any other.

   A middle of different lengths also replaces equal items inside it. For example, an insert at 0 plus a relabel
   at 5 replaces positions 0-5. That is bounded and accepted (round-2 #6).
3. **`same_item()`:**
   - the same set of attribute names, each equal by `g_variant_equal` (all attributes, round-1 Q2);
   - the same set of link names.
   - The linked objects are not compared here. Their contents are synced by the recursion.
4. **Which models are ours: a mark on the object, not a set (round-2 #1).**
   - `clean_model` marks every `GMenu` it creates with `g_object_set_data(out, "unity-gtk4-menu-copy", 1)`.
     `look()` marks `inner` the same way.
   - The mark lives and dies with the object, so it cannot outlive it. A freed copy whose address is reused by an
     application's `g_menu_new()` is not mistaken for ours, and throwaway copies need no cleanup.
     `g_object_set_data`/`get_data` are already resolved (:274-275).
   - **Recursion rule:** `sync()` recurses into a link only if our link object *and* the new copy's link object
     both carry the mark. Otherwise it compares the two objects by pointer, and replaces the item if they
     differ.
   - So an application model is reached only by a pointer comparison, never edited, whatever the depth. This
     covers depth 16 and more, where `g_menu_item_new_from_model` copied the application's own link object
     (:1021), and links other than `section` and `submenu` (round-1 #3).
5. **No change, no signal.** A burst that ends where it began emits nothing.

**Accepted cost, documented (round-1 #7):** relabelling an item whose own submenu is open collapses that
submenu, because the replaced item's submenu link gets a new group. GMenu has no way to change an item's
attributes in place. Siblings and other submenus are untouched.

### 4. When watching stops

- **`go_taken` and `record_free`:** remove the idle, unwatch, and drop `source` (round-1 #6).
- **The window or widget gone at a rebuild:** step 2.3.
- The watch list's references keep each model alive while it is watched, so the finalization order is safe.

### 5. Stand-ins (round-1 #4, Q4)

- The rebuild's `clean_model` runs `proxy_item` for the filling window, as at the fill.
- **The other windows.**
  - The `action` values of the **source** model (before stand-ins rename them, :943) are collected at each
    rebuild and compared with the previous rebuild's (round-2 #4).
  - For names that are new, every other `GtkApplicationWindow` of the application (`gtk_application_get_windows`)
    gets `proxy_for(name, its_owner, its_map)`.
  - `its_owner` is that window's own menu widget, found with `find_menu_model` on it with `late = 0`, so it adds
    no `watch_late` on that window (:540-546).
  - A window without one gets none, as today.
  - No full copy per window.

### New symbols through RESOLVE

- `g_menu_remove` and `g_menu_insert_item`;
- `g_menu_model_iterate_item_attributes`, `g_menu_attribute_iter_get_next`, `g_menu_model_iterate_item_links`,
  `g_menu_link_iter_get_next`;
- `g_variant_equal`;
- `gtk_application_get_windows`.

The mark needs nothing new (round-2 #1).

Fail-closed as today.

## Tests

latetest, Xvfb, both preload forms, `G_DEBUG=fatal-criticals`; a counter of `items-changed` connected by the test
to the models it names; a D-Bus client that records `Changed` signals.

- **13. Relabel in a section.**
  - `items-changed` on that section's GMenu: 2; on `inner` and `container`: 0.
  - `Changed` on D-Bus: exactly 2, for that section's group and menu ids.
  - A new `Start` shows unchanged ids for every untouched section and submenu.
  - The label reaches the client.
- **14.**
  - An insert at position 0, an insert in the middle and a removal touch only the changed items.
  - A burst of 100 changes gives one rebuild.
  - A change that is undone in the same burst emits nothing.
- **15.** A section link switched to a new model object: a change on the old object does nothing, one on the new
  one rebuilds.
- **16.** A section that cleans to nothing, then becomes non-empty again.
- **17.** The filling window closed while another stays, then a change: no rebuild, one log line, the copy
  unchanged.
- **18.** The owner destroyed with an idle pending, and the application quit in the same turn as a change: no
  critical, no handler after finalize (also under valgrind).
- **19.** A model nested deeper than 16 levels, changed below 16:
  - the application's model is not edited;
  - the item is replaced only if the application replaced the link object;
  - a change inside that model reaches the D-Bus client through the exporter, which watches it directly
    because it is linked into our tree (gmenuexporter.c:291) (round-2 #3).
- **20.** A second window: a new action in a changed item gets its stand-in in that window's map, pointing at
  its own owner.
- **21.** An application that never changes its menu: 0 rebuilds over the run. A rebuild of a 200-item model,
  timed.
- **22.** A throwaway copy from a second window's realize, then a rebuild, under valgrind: the guard against the
  reuse of a freed copy's address (round-2 #1).
- **Target 4, Nautilus:**
  - a rename (`research/nocsd-gaps/tests/naut.sh` and by keys) shows "Отменить переименование" in the export
    (`menudump.py`), and the HUD finds it;
  - with two windows, a rename in each, to document what follows and what does not.
- **Target 5, an open panel menu.** A test application changes its menu every 2 s while a panel menu is open,
  judged by events:
  - popwatch: the popup stays mapped;
  - Sync: the entry keeps its id;
  - after reopening, the latest label.
  - **First the oracle:** the same application doing `remove_all` and re-adding must make popwatch report the
    collapse. Only then does a pass mean something.
  - Cases:
    - (a) the holder's menu open, a sibling item relabelled;
    - (b) a submenu open, an item inside it relabelled;
    - (c) a submenu open, an item outside it relabelled.
    - (b) collapses by the accepted cost above only if that submenu's own item changed, not an item inside it.
- **Regression:**
  - latetest 1-12;
  - order-0.9.sh unchanged;
  - Pinta (filled late, then Undo enabled after a stroke reaches the panel);
  - the UNITY-20261012-003 set by events.
- **Control:** 0.12 fails 13 and target 4 (stale). Target 5 has no control, since 0.12 never edits the copy; the
  oracle replaces it.

## Round-1 findings and where they are answered

| # | finding | answer |
|---|---|---|
| 1 | positional compare storms on insert/remove | 3.1-3.2: prefix/suffix trim, only the middle edited; tests 14, 16 |
| 2 | a rebuild after the window or widget is gone corrupts the copy | 2.3: no rebuild, unwatch, log once; test 17 |
| 3 | below depth 16 our copy links the application's model | 3.4: pointer compare and replace there, ours recognised by a mark on the object (round 3); test 19 |
| 4 | the other windows' stand-ins | 5: only new names, each window's own owner, no copy; test 20 |
| 5 | watching our own menus | 1: skip container/inner and listed models; 2: `syncing` flag |
| 6 | the idle's lifetime | 2.1-2.2 and 4; the watch starts in `look()` |
| 7 | relabelling an item whose submenu is open collapses it | 3, documented as an accepted cost; target 5(b) |
| 8 | with two windows only the first is followed | known limit, linked to UNITY-20261013-028; target 4 documents it |
| 9 | UNITY-20261013-024 out of 0.13 | kept out; BACKLOG |

## Round-2 findings and where they are answered

| # | finding | answer |
|---|---|---|
| 1 | the "ours" set can keep freed addresses (ABA) | 3.4: a mark on the object; recursion only if both sides are marked; `inner` marked; test 22 |
| 2 | prefix and suffix must not overlap | 3.1: the suffix bounded by `min(n_old, n_new) − prefix` |
| 3 | test 19's expectation | test 19 reworded |
| 4 | compare action names before stand-ins; `late = 0` | 5 |
| 5 | changes during a rebuild are lost | 2, accepted and documented |
| 6 | a middle of different lengths replaces equal items too | 3.2, accepted |
| 7 | the idle's priority | 2: `G_PRIORITY_DEFAULT_IDLE` |

## UNITY-20261013-024 (a menubar the application sets after realize), weighed

Putting the application's menubar into our container would need our container set back as the application's
menubar. That changes the application's own `gtk_application_get_menubar()`, and GTK's in-window menubar when the
shell shows none. Making the panel subscribe again belongs to unity. The survey (logs/02) found no application
that does it, so UNITY-20261013-024 is BACKLOG.
