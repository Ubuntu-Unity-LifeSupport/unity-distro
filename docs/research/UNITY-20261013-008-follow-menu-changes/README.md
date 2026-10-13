# unity-gtk4-menu: follow menu changes after the first export (UNITY-20261013-008)

Owner: agent B (target2). Target version: 0.13 (0.11 and 0.12 are published).

```yaml
task: UNITY-20261013-008
title: unity-gtk4-menu 0.12 exports a copy made when the menu is found and never updates it; stale or wrong global menus in Nautilus, Papers (and Console, per the UNITY-20261012-004 survey)
package: unity-gtk4-menu (0.12 live)
target_series: resolute
status: PUBLISHED - 0.13 published 2026-10-13 20:39:06Z (snapshot unity-resolute-20261013-008), verified on target2
```

## Measurement (2026-10-13, target2)

target2: Clean-2, the live archive with unity-gtk4-menu 0.12 and unity-session 49.4+unity2, a cold session with
both libraries preloaded. Installed for the test: nautilus 1:50.2.2-0ubuntu0.2, papers 50.2-0ubuntu0.1,
gnome-console 49.2-1.

Each application was started in the session's environment with the library's debug log, and its window
activated.
- **What the panel gets:** the window's exported menubar, read the way the panel reads it (`menudump.py`: a
  `GDBusMenuModel` client walked recursively, every subscribed group kept referenced).
- **What the application has:** its own menu button opened, and a screenshot of it (the screenshots are
  supporting evidence only).
- **The change:** made from the host with keys.

Log: `logs/01-exported-now.txt` (the exports and the library logs, taken with the windows still in the state below).

| application | at realize | the change | the application's own menu after it | the export after it |
|---|---|---|---|---|
| Nautilus | main menu (8 items) chosen and copied: "Создать _окно", "Создать _вкладку", "_Отменить", "_Повторить", … | a file renamed (F2, a new name, Enter) | "Отменить переименование" (Undo Rename), `nautilus-own-menu-after-rename.png` | still "_Отменить" (Undo): **stale** |
| Papers | in the start view, the sidebar's main menu (3 items: Keyboard Shortcuts, Help, About), chosen over 4 hidden candidates | a PDF opened in the same window (Ctrl+O) | the document view adds a second menu button, "Меню документа" (Document menu), with 14 items: Print, Fullscreen, Presentation, Digital Signature, Open a Copy, Open With, Save As, Continuous, Dual, …, Properties (`papers-own-document-menu.png`) | still the start view's 3 items: **the document menu never reaches the panel** |
| Console (kgx) | its main menu (6 text items; 4 widget items dropped, as designed) | a second tab (Ctrl+Shift+T) | the same 6 text items (`console-own-menu.png`) | the same 6 items: **not stale** in this scenario |

## What the cases need

- **Nautilus** changes the **same** model that was copied. When it relabels Undo, it emits `items-changed` on a
  section of its main menu. Following `items-changed` on the source model and its sections and submenus, and
  updating our copy in place, fixes it.
- **Papers** does not change the copied model. It shows a **different** menu button in the document view. Only
  a new look after the first fill, on the map of another menu button, can find it: the "follow the shown menu"
  of the gtk-nocsd series. A new look would also have to decide which of two shown menus the panel gets: the
  sidebar's main menu or the document menu.
- **Console** needed nothing here. The survey's "a hidden page's menu" did not happen with the menu found at
  realize, in this scenario.

So the scope C named for 0.13 (`items-changed`: replace the one holder item, skip unchanged copies, no `Changed`
storm, an open panel menu must not collapse) covers **Nautilus**. **Papers** needs the second mechanism. Whether
it belongs in 0.13 is a design question.

Prior art: our gtk-nocsd series, upstream as GTK-NoCSD `2d50fe9` "Find menus added late and follow menu changes"
(research/nocsd-gaps):
- it follows `items-changed` of the menu and of every section and submenu, coalesced into one idle rebuild;
- it follows the shown menu with a `map` emission hook on menu buttons, searching again and switching when
  another button shows another menu.

Related: UNITY-20261013-024 (a menubar the application sets after realize) is to be weighed in this design.

## UNITY-20261013-024's survey (logs/02)

13 GTK 4 applications were each started for 15 s in a Unity session with 0.12: nautilus, papers, kgx, epiphany,
gnome-contacts, gnome-text-editor, gnome-characters, gnome-calculator, gnome-clocks, gnome-font-viewer,
gnome-weather, gnome-tweaks and gnome-tour.
- **None sets a menubar of its own after ours** ("ours is released": 0 in every run). None had one before realize.
- 10 are filled at realize. gnome-contacts, gnome-font-viewer and gnome-tour wait without a menu.

So the takeover case is synthetic so far (`takeover.py`), and UNITY-20261013-024 stays BACKLOG.

## A side finding: epiphany aborts on SIGTERM with gtk-nocsd (logs/03)

The survey ended each application with SIGTERM, and epiphany aborted. `epiphany-term.sh` repeats it, with every
epiphany ended first, so each run starts the primary instance itself. 3 runs each:

| preload | exit |
|---|---|
| the session's (both libraries) | 134, SIGABRT: `epiphany:ERROR:../src/ephy-main.c:459:main: assertion failed: (!ephy_shell)` |
| libgtk-nocsd.so.0 only | 134, the same assertion |
| none | 143, an ordinary SIGTERM |

So it is gtk-nocsd 4.8-1+unity4, not unity-gtk4-menu. Most likely gtk-nocsd keeps the application object alive past
the end of `main()`, so EphyShell is not finalized when epiphany asserts it is. This is not part of this task; it
is reported to C. A session's logout sends SIGTERM, so an open epiphany would abort then.

## Design review round 1 (Design Challenger, 2026-10-13): REVISE

The direction was confirmed: keep the source, one idle per burst, edit our copy in place at the deepest changed
level. The Challenger read GLib 2.88's `gmenuexporter.c`:
- a changed position gets new links, a `submenu` link always a new group;
- untouched positions keep their ids;
- every `items-changed` sends one `Changed` at once.

Blocking:
- (1) a position-by-position comparison turns an insert or removal into a storm;
- (2) a rebuild after the filling window or widget is gone loses the stand-ins and corrupts the copy;
- (3) below depth 16 our copy links the application's own model, which `sync()` must never edit.

Should:
- (4) the other windows' stand-ins: only new names, each with its own owner;
- (5) never watch our own menus;
- (6) the idle's lifetime.

Notes:
- (7) relabelling an item whose submenu is open collapses that submenu, unavoidable with GMenu;
- (8) with two windows only the first is followed;
- (9) UNITY-20261013-024 rightly out.

DESIGN.md round 2 answers each finding (its last table).

## Design review round 2 (Design Challenger, 2026-10-13): REVISE

One blocking finding:
- (1) a set of our copies keyed by pointer can keep freed throwaway copies' addresses, which the application's
  `g_menu_new()` may reuse (ABA). The fix is a mark on each copy (`g_object_set_data`), with recursion only when
  both sides carry it.

Notes:
- (2) the prefix/suffix bound;
- (3) test 19's wording;
- (4) the source's action names, and `late = 0`;
- (5) changes during a rebuild are lost (accepted);
- (6) a different-length middle replaces equal items inside it;
- (7) the idle's priority.

DESIGN.md round 3 answers them (its second table).

## Design review round 3 (Design Challenger, 2026-10-13): APPROVE

All seven round-2 findings are answered, the blocking one included: copies are recognised by a mark on the
object, and recursion happens only if both sides are marked.

Notes for the implementation:
- seed the source's action names at the fill;
- skip recursion when our link object and the new one are the same pointer (a self-referencing source below
  depth 16);
- a private mark key with `GINT_TO_POINTER(1)`;
- a hard depth cap of 16 in `sync()`.

The tests that guard the riskiest paths are 13, 14, 19, 22 and target 5, the last only after the oracle check.

## Implementation (0.13, package branch b/UNITY-20261013-008)

Per DESIGN.md round 3, in `src/unity-gtk4-menu.c`:
- **The copy mark.** `clean_model()` puts the mark `unity-gtk4-menu-copy` on every GMenu of a copy, and on
  `inner`. `is_copy()` reads it.
- **Following.** After a fill, `look()` calls `start_following()`, which keeps:
  - the source model (a ref);
  - the owner and the window (weak pointers);
  - the source's action names (seeded at the fill).

  `watch_model()` connects `items-changed` on the source and on every section and submenu down to depth 16, the
  depth `clean_model()` copies to (`MAX_DEPTH`). Below it the copy links the application's own models, and the
  exporter watches those itself. Our container and inner, and models already watched, are skipped.
- **One rebuild per burst.** `on_source_changed()` schedules one default-priority idle unless one is pending or a
  sync is running. `rebuild_idle()` works on a state of `OURS_FILLED` only.
  - If the window or widget is gone, it logs "no longer followed" once and stops following. The copy is kept.
  - Otherwise it unwatches, copies the source again with the same scope, and syncs the copy into `inner`. It then
    adds stand-ins in the other application windows for action names new since the last copy, and watches again.
    It logs "menu changed (rebuild N): K item(s) replaced".
- **`sync_menu()`.**
  - It keeps the common prefix and suffix; the suffix is bounded by min − prefix.
  - Kept items have their links synced: recursion happens only when both link objects carry the mark and differ.
    An unmarked link of the application that differs replaces the item.
  - Only the middle is edited: item by item when both middles have the same length, otherwise the old middle is
    removed and the new one inserted.
  - The suffix is processed first, then the prefix, then the middle.
  - Depth cap 16.
- **`same_item()`** compares every attribute (names and values with `g_variant_equal`, both ways) and the link
  names.
- **Stopping.** Following stops on TAKEN and in `record_free()`: the idle is removed, every handler disconnected,
  the source dropped, and the weak pointers removed.
- **New symbols**, resolved like all others: `g_menu_remove`, `g_menu_insert_item`, the attribute and link
  iterators, `g_variant_equal`, `gtk_application_get_windows`. NEEDED stays libc only.
- An off-by-one found while writing test 19: the watch first stopped at depth 15 while the copy reaches 16, so a
  change at depth 16 would have been missed. It was fixed before any test ran (commit d377096).

## Tests

### latetest 13-22 (`tests/latetest.c`), Xvfb, target2

The cases are described in the file's header.
- A D-Bus side reads the export the way the panel does: org.gtk.Menus Start on every reachable group, and a count
  of the Changed signals with their group/menu ids.
- Counters of `items-changed` are connected to our copies and to the application's models.

Results:
- **0.13** (the sbuild deb, `libunity-gtk4-menu0_0.13_amd64.deb` sha256 e979cf29…, installed on target2;
  `logs/06-latetest-0.13.txt`): 20 of 20 pass (cases 1-12 and 13-22). Case 21 timed the rebuild of 200 items at
  2.8 ms, from the change to the log line. NEEDED is libc only.
- **valgrind** (memcheck): 0 errors on 13, 18, 19 and 22 against the deb (`logs/07`), and on 13, 17, 18 and 22
  against the same source built on target2.
- **0.12 control** (`logs/05-latetest-0.12-control.txt`, `LATETEST_CONTROL=1`): 13, 14, 15, 16, 19, 20 and 22 fail,
  because nothing follows. 17, 18 and 21 pass, as they should on both versions: they check that nothing breaks
  or is rebuilt when nothing may be.

### Regression (`logs/07-regression-0.13.txt`)

The UNITY-20261012-004 set (`runtests.sh`: latetest 1, 1f, 2, 3, 3f, 4, 5, 7, 8, 9, 11, 12, adw6 and adw6a) against
the installed 0.13:
- 14 of 14 with the session's preload;
- 14 of 14 with the library preloaded alone.

### Target 4: Nautilus (`t4-nautilus.sh`)

A cold Unity session on target2. F2, Enter, Ctrl+Z and Ctrl+N come from the host (vbox `send_keys`): xdotool's F2
opens Unity's run dialog on this keymap and never reaches the window. The judges are the export (`menudump.py`) and
the HUD (`hudq.py "переименование"`).

| step | 0.12 (`logs/04`, control) | 0.13 (`logs/08`) |
|---|---|---|
| a rename by keys | export "_Отменить", HUD 0 results: **stale** | "_Отменить переименование"; HUD "Отменить переименование (Файлы)" |
| Ctrl+Z | - | "_Отменить" and "_Повторить переименование"; HUD "Повторить переименование" |
| a rename through FileOperations2 RenameURI | "_Отменить", HUD 0: **stale** | "_Отменить переименование"; HUD finds it |
| a second window (Ctrl+N): a rename and Ctrl+Z in window 2 | - | both windows' exports follow each step |
| window 1 closed, then a rename | - | window 2's export follows (rebuild 3) |

The 0.12 control directory also held a file left by an earlier dry run (`alpha-renamed`). `t4-nautilus.sh` now
clears the directory.

Nautilus's undo menu belongs to the application, so window 1's copy follows a change made in window 2. After window 1
was closed (xdotool windowclose), the rebuild still ran: its window and menu button were not finalized yet, so the
weak pointers were still set. "No longer followed" is covered by latetest 17 (and under valgrind) rather than here.

### Target 5: an open panel menu (`t5.sh`, `t5app.py`, `popwatch2.c`), `logs/09`

`t5app.py` changes its menu every 2 s. The judges are events:
- `popwatch2`, an Xlib poll every 20 ms of unity-panel-service's mapped override-redirect popups with their geometry;
- `sync.sh`, the panel's entry id;
- the application's change lines;
- the export and the library log.

`popwatch.sh` from UNITY-20261012-003 counts windows through xdotool, and its count did not change when a submenu
opened or closed, so it cannot see a collapse. `popwatch2` sees the holder's menu (89,30 125x104) and "Sub" (212,82
108x52) as separate windows.

| mode, what is open | what changes | popups | entry id | result |
|---|---|---|---|---|
| `sub` (the oracle), Sub open | "Sub" itself relabelled | Sub's window goes away 1.3 s after it opened, right after a change | kept | **collapse seen**: the probe works |
| (a) the holder's menu | "Tick N", a sibling | the holder's menu maps at 18:09:36.682 and does not change until popwatch ends (16 s from its start), across changes 2-9; a screenshot at 18:09:51Z (supporting only) shows "Tick 9" in the open menu | kept | PASS |
| (b) Sub | "Inner N", inside Sub | both stay to the end | kept | PASS |
| (c) Sub | "Outside N", outside Sub | both stay to the end | kept | PASS |
| `all`, Sub open | every item removed and added again (`remove_all`), only "Tick N" new | both stay; "1 item(s) replaced" per change | kept | PASS |

The design named `remove_all` as the oracle. With 0.13 it cannot collapse anything: the burst is coalesced and the
sync replaces only the changed item, as mode `all` shows. So the oracle is the one change that must collapse: a
relabel of the item whose submenu is open, the accepted cost.

## Verification (2026-10-13)

An independent Verifier (an ephemeral general-purpose subagent) reviewed d377096 and this card. **Verdict: PASS.**
- The code follows DESIGN.md round 3. The sync index arithmetic, the reentrancy, the depth caps and the lifetimes
  were checked.
- The deb's source is byte-identical to d377096, and NEEDED is libc only.
- Tests 13-22 check what the design lists, and the 0.12 control fails for the right reasons.
- The target 4 and 5 logs match this card. The target-5 oracle (a relabel of the open submenu's own item, not
  `remove_all`) is sound.

Non-blocking notes:
- `add_stand_ins()` looks up the menu in every other window at every rebuild, even with no new action names. That
  costs time and adds one log line per window. An early return is a candidate for later.
- `watch_model()` skips only container and inner, as the design says. An `is_copy()` skip would guard an application
  that embeds one of our copies.
- Mode (a)'s wording here was corrected to the logged times.
- The oracle shows a submenu collapse only. That the holder's own popup would collapse the same way rests on the same
  mechanism.
- A closed Nautilus window that has not been finalized is still followed (above).

## Known gaps (named for the release)

- UNITY-20261013-028: Papers' document menu is a different menu, shown later, and is not followed.
- UNITY-20261013-024 (BACKLOG): a menubar the application sets after realize.
- UNITY-20261013-030: `add_stand_ins()` looks up the menu in every other window at every rebuild (the cost grows with
  the number of windows).

## Publication (2026-10-13)

The slot steps were:
- origin/main merged;
- the db backup `~/backups/UNITY-20261013-008-20261013T202025Z` (list sha256 23f049c2…);
- `repo add` of the manifest's `.dsc`, `.deb` and `.ddeb`, with the pool sha256 equal to the manifest;
- the snapshot `unity-resolute-20261013-008`, which is the live `unity-resolute-20261008-023` plus the three records
  (`gate/snapshot-diff.txt`);
- version safety SAFE;
- the peer ACK from A;
- the gate as the last commit (f0945e8, sha256 903d9fbd…);
- C's approval, with the gaps UNITY-20261013-028, UNITY-20261013-024 and UNITY-20261013-030.

The signer's daily limit stopped the first run (proposal e3db23e7332ab479), and May approved it on the console. The
next run stopped in the publisher's apt view on a transient outage of de.archive.ubuntu.com. Live was unchanged and
the approval unused, so the same command ran again and switched. Published 2026-10-13T20:39:06Z.

Target verification on target2 (`gate/target-verification.txt`, logs/10-14):
- Clean-2 → live (0.12), then the upgrade from live to 0.13. The downloaded deb is the gated one (e979cf29…).
- In a cold session, Nautilus's export and HUD follow Undo/Redo Rename.
- The gtk-nocsd opt-out cold session has 0 AssertionError lines, and the PyGObject programs show their windows.
- target2 was restored to Clean-2 afterwards.
