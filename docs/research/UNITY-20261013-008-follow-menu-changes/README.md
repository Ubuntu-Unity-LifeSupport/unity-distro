# unity-gtk4-menu: follow menu changes after the first export (UNITY-20261013-008)

Owner: agent B (target2). Target version: 0.13 (0.11 and 0.12 are published).

```yaml
task: UNITY-20261013-008
title: unity-gtk4-menu 0.12 exports a copy made when the menu is found and never updates it; stale or wrong global menus in Nautilus, Papers (and Console, per the UNITY-20261012-004 survey)
package: unity-gtk4-menu (0.12 live)
target_series: resolute
status: INVESTIGATING - staleness measured; design next (Design Challenger before code)
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
