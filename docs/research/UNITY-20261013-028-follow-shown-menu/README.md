# unity-gtk4-menu: follow the shown menu, not only the one copied at realize (UNITY-20261013-028)

Owner: agent B (target2). Series: unity-gtk4-menu 0.14 with UNITY-20261013-030 and UNITY-20260927-039
(`DESIGN.md`).

```yaml
task: UNITY-20261013-028
title: unity-gtk4-menu keeps the menu chosen at realize; Papers' document view shows another main menu
package: unity-gtk4-menu (0.13 live)
target_series: resolute
status: reproduces (2026-10-17); design for the Design Challenger in DESIGN.md
```

## Background

UNITY-20261013-008 measured on 0.12: Papers opened with a PDF in the same window keeps the start view's 3 items on
the panel, while the document view shows a "Document menu" of 14 items. Following the shown menu was left out of 0.13
by scope.

## Measured (2026-10-17, target2; `probe.sh`)

target2: Clean-2 → live (InRelease 2026-10-17 06:06:43 UTC), with:
- libunity-gtk4-menu0 0.13 and libgtk-nocsd0 4.8-1+unity5;
- papers 50.2-0ubuntu0.1 from the archive;
- a cold Unity session.

Papers was started in the session's environment with the library's debug log. The export was read the way the panel
reads it (`menudump.py` of UNITY-20261013-008).

| run | log | window | the library at realize | export |
|---|---|---|---|---|
| `papers doc028.pdf` | 02 | document view | candidates 1 (shown, primary, 3 items) and 5 (hidden, primary, 5 items); **chose 1** | Keyboard Shortcuts, Help, About |
| `papers` alone, then a second `papers doc028.pdf` | 02 | the second is a process of its own, with its own window and the same choice | as above | as above |
| `papers` alone, then Ctrl+O in the same window | 03 | the same window (60817412 → title "doc028.pdf") and the same process (pid 8222) | no new look | **unchanged: the start view's 3 items** |

Notes on the runs:
- Papers runs one process per document. The start view becomes a document view in the same window only through its
  own Open dialog (logs/02, 03).
- The dialog is xdg-desktop-portal-gtk's window and opens behind Papers without focus. The probe activates it.
- The probe also unlocks the session first: in one attempt light-locker had locked the screen and took the typed path
  as a password. Those keys reached no application, and the earlier runs typed nothing.

## The candidates, from Papers' source

papers 50.2 (`shell/resources/pps-window.blp`, `pps-document-view.blp`):

| candidate | widget | model | primary | app./win. items | items in all |
|---|---|---|---|---|---|
| 1 | the start page's `MenuButton` (`pps-window.blp`:33) | `app_menu`: Keyboard Shortcuts, Help, About | yes | 3 | 3 |
| 3 | `document_menu_button`, "Document Menu" (⋮), document view | `document_menu`: Print, Fullscreen, Present, Sign, Open a Copy, Open With, Save As, Continuous, Dual, Odd Pages Left, Right to Left, Rotate, Properties | no | 2 (win.fullscreen, win.presentation) | 13 |
| 5 | `action_menu_button`, "Main Menu" (☰), the sidebar's header | `sidebar_menu`: Open…, Night Mode, Keyboard Shortcuts, Help, About | **yes** | 5 | 5 |

Candidates 2 and 4 have no app./win. items.

So the document view shows two menu buttons at once (`papers-document-view.png`):
- the sidebar's **Main Menu** is the one Papers marks primary (F10). It is the document view's counterpart of the
  start view's menu.
- the **Document Menu** is the menu UNITY-20261013-008 saw, counted there as 14 items on screen. The source has 13,
  and 11 of them name `doc.*` actions, a group
  Papers inserts on its document view (`gtk_widget_insert_action_group`). 0.13 gives stand-ins only to class actions
  and logs other prefixes as unreachable. Copied to the panel today, it would be 11 greyed-out items out of 13.

What the panel should get after the switch is candidate 5. The ranking 0.13 already uses gives exactly that once it
is applied again:
- shown, then primary, then app./win. items;
- candidate 1 is hidden with its stack page, candidate 5 is shown and primary.

## Correction to UNITY-20261013-008's table

Its Papers row reads "the sidebar's main menu (3 items: Keyboard Shortcuts, Help, About)" for the start view, and
"Document menu, 14 items" as what the document view adds. By the source and these logs:
- the start view's menu is the start page's own (`app_menu`), not the sidebar's;
- the document view adds two buttons. The sidebar's Main Menu (5 items, primary) is the one the panel should follow;
  the Document Menu (13 items in the source) is mostly `doc.*`.

## Prior art

Our gtk-nocsd series has the same mechanism:
- GTK-NoCSD `2d50fe9` / our `60ec176`, `GTKNoCSDMenuFollowShown` and `GTKNoCSDMenuButtonMap`, `Source/GTK-NoCSD.c`
  :5413-5474: an emission hook on `map` of GtkMenuButton in the followed window, an idle re-search, and a switch when
  another model is found.
- The shipped gtk-nocsd 4.8-1+unity5 has no menu code (UNITY-20261012-004, "What we ship").
- unity-gtk4-menu is the component that exports GTK4 menus here, so the mechanism belongs in it (DESIGN.md, "Weighed").

## Files

- `probe.sh`: setup, withdoc, startview (on target2 as mike, with `menudump.py` from UNITY-20261013-008 in `~/b028`).
- `logs/01-setup.txt`, `logs/02-papers.txt` (withdoc, and the second-process run), `logs/03-papers-open.txt` (Ctrl+O in
  the same window).
- `papers-document-view.png`: the window after Ctrl+O, with both menu buttons.
- `xsession/cases.sh`, `logs/04-xsession-cases.txt`: the UNITY-20260927-039 part of the design. The prototype snippet
  sourced after the installed 51gtk-nocsd on target2, in ten cases.
