# unity-gtk4-menu 0.12 on a desktop: an empty menubar, and an application that takes over (UNITY-20261013-023)

Design tests 3 and 5 of UNITY-20261012-004 (DESIGN.md, "Tests"), left out of its gate and measured here on
target2 against the published 0.12, with 0.11 as the control. This task only records the results; nothing was
changed.

Setup: target2 with the live archive (InRelease Date 2026-10-13 14:31:08 UTC), libunity-gtk4-menu0 0.12 from it
(0.11 from it for the control), cold boots with autologin into Unity, both libraries preloaded (the session's
default). Outcomes come from events, not screenshots:
- the panel service's entry table (`sync.sh` of UNITY-20261012-003 and its full `Sync` table);
- its popups (`popwatch.sh`) and its `ShowEntry` / `EntryActivated` (dbus-monitor);
- what hud-service returns for a query for the focused window (`hudq.py`, `StartQuery` / `CloseQuery`);
- the library's debug log.

Keys come from the host (vbox `send_keys`). Script: `t3t5.sh`; the test-5 application: `takeover.py`.

## Test 3: a window with no menu, the empty menubar (gnome-tour)

| | 0.11 (logs/04) | 0.12 (logs/01) | 0.12, integrated menus on (logs/05) |
|---|---|---|---|
| `_GTK_MENUBAR_OBJECT_PATH` | none | `/org/gnome/Tour/menus/menubar` (the empty menubar) | the same |
| library | (no late look in 0.11) | empty menubar set, the window waits, no look, no fill | the same |
| panel entries for the window | 0 | 0 | 0 |
| Alt+F10 | opens the first indicator, `a11y-profile-manager-indicator` (ShowEntry, EntryActivated) | the same (popup mapped; the Accessibility menu is open on the screen) | not sent |
| HUD for "a" and "tour" | 0 results | 0 results | 0 results |

The empty menubar is exported, but nothing in the shell shows it: no panel entry and no HUD results. The keys do
what they do for any window without a menu, the same as with 0.11.

## Test 5: the application sets a menubar of its own after realize (TAKEN)

`takeover.py`: a window with a header bar and no menu at realize, which sets its own menubar (_File, _Edit, _Help)
5 s after present.

| | 0.11 (logs/03) | 0.12 (logs/02) | 0.12, integrated menus on (logs/05) |
|---|---|---|---|
| `_GTK_MENUBAR_OBJECT_PATH` | none | `/org/unitydistro/TakeOver/menus/menubar` | the same |
| library | - | empty menubar set, the window waits; then "the application set a menubar of its own; ours is released", the window stops waiting | the same |
| exported at the menubar path after the takeover (a fresh `org.gtk.Menus.Start`) | `_File`, `_Edit`, `_Help` | `_File`, `_Edit`, `_Help` | - |
| panel entries for the window, 6-7 s after the takeover | 0 | 0 | 0 |
| Alt+F | no popup | no popup | not sent |

**What happens.** The library releases its menubar as designed, and GTK exports the application's own menubar
at the same path. A fresh subscriber sees it. But the panel does not show it. With 0.12 the panel subscribed to
the empty menubar first, and nothing tells it the export was replaced. With 0.11 the window never had a menubar
path, because GTK writes it only at realize. **The result is the same in both versions: an application that sets
its menubar only after realize has no global menu.** 0.12 is no worse than 0.11 here.

## Result

- No regression from 0.11 in either test; nothing to fix for 0.12.
- Design test 5 shows a case neither version handles: a menubar set by the application after realize.
  - With 0.12 the window already has a menubar path. A fix could keep our container exported and put the
    application's menubar into it, instead of releasing it, which is the round-3 design's TAKEN rule. Or it could
    make the panel subscribe again.
  - This changes the design, so it is a question for C, not part of this task.
- The first test-3 attempt does not count: the HUD's own window, left open by the HUD test, held the focus
  (logs/01).
