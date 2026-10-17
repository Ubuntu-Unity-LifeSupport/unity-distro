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

## Design review round 1 (2026-10-17): REVISE

The Design Challenger (a separate subagent following `.claude/agents/design-challenger.md`) returned REVISE with two
blocking and six should-fix findings, and two notes. In short:
1. (blocking) A destroyed owner made the relook stop following.
2. (blocking) Stand-ins reused across a switch kept the old owner and holder.
3. Case F left ours behind gtk-nocsd.
4. A hidden non-primary menu could stick.
5. A realize-time menu outside header bars could never come back.
6. Lifetime of the idles and the handler id.
7. How `in_titlebar` is computed for the map filter.
8. The prototype and the R/R2 cases were not in the card, and the 51gtk-nocsd cited was +unity3.
9. B (note): correct.
10. (note) Case D with ssh-agent, and T7 needs the user manager gone.

On part C, point 1, it agreed with `libunity-gtk4-menu0` and asked for the Policy 8.2 deviation to be recorded in
DECISIONS. C accepted the same on 2026-10-17.

Each finding is answered in DESIGN.md round 2 (the table at its end).

## Design review round 2 (2026-10-17): REVISE

One blocking finding: an owner that is gone with no other menu shown yet stopped following, so a view built later was
never seen. Three should-fix findings:
- a gone primary menu kept a fewer-item replacement out;
- the same model behind a new owner was ignored;
- `proxy_free` could clear a new stand-in's key.

Notes:
- the `unmap` handler id wording;
- a developer's own build in `LD_PRELOAD` would have been replaced;
- test numbering.

It found no remaining case with a live owner where the rule keeps a dead menu or flips to a wrong one, and confirmed
the prototype and cases A-J, R and R2 against gtk-nocsd +unity5. Each finding is answered in DESIGN.md round 3.

## 0.14: built and tested (2026-10-17)

Package: `packages/unity-gtk4-menu` on branch b/UNITY-20261013-028, commits `93e99d6` (B), `72eb308` (A), `2acd1c1`
(C), `63e56cf` (tests), `e308fc5` (release). Built with `scripts/build_sbuild.py` in the 2026-10-17 chroot
(`build-0.14/`, manifest and sbuild log). Lintian has only the warning 0.13 already had (`pkg-config` → `pkgconf`).
The deb ships `/etc/X11/Xsession.d/52unity-gtk4-menu` as a conffile, byte for byte `data/52unity-gtk4-menu`.

All runs are on target2: Clean-2 → live, then 0.14 installed from `build-0.14/`.

| test | log | result |
|---|---|---|
| latetest 1-35, 1f, 3f, adw6, adw6a, against the installed 0.14 | 09 | 37 of 37 pass |
| the same under valgrind, cases 18, 22, 27, 28, 35 | 09 | 5 of 5, no error |
| a development build before the package; control: 0.13 installed, cases 23-35 | 08 | 0.14 33 of 33; 0.13 fails 23, 25, 26, 27, 28, 29, 30, 31, 33 (24, 32, 34, 35 assert nothing happens) |
| T1 Papers alone, then Ctrl+O | 10 | the export becomes `sidebar_menu`: Open…, Night Mode, Keyboard Shortcuts, Help, About. Sidebar hidden: kept (the doc menu not taken); shown again: nothing to do (its own owner) |
| T2 Papers with the PDF at start | 10 | the 600 px window opens with the sidebar **collapsed**: only the Document Menu shows, and the start page's menu is kept (all `app.*`). DESIGN's expectation ("the sidebar maps, a relook switches") assumed a visible sidebar. Sidebar shown: switched to `sidebar_menu`; closed again: kept |
| T3 Console, tab overview opened and closed | 11 | switched to the overview's menu (New Window, Fullscreen, Leave Fullscreen) and back to the main menu; stand-ins moved each time; the HUD finds "Новое окно" in all three states |
| T5 Nautilus, three windows, 20 renames (FileOperations2.RenameURI) | 12, 12b | 0.14: 20 rebuilds, 0 window looks; 0.13 (the same run with 0.13 preloaded): 20 rebuilds, 40 window looks; "Отменить переименование" exported |
| T4 the -1013-024 survey of 13 applications | 13 | no switch, orphan, adoption or release anywhere; relooks in nautilus and gnome-calculator, each without a change. gnome-text-editor shows no fill here because a D-Bus-activated instance (`--gapplication-service`) was already running; started alone it fills as before (6 items) |
| T4 preload orders (order-0.9.sh's set, packaged gtk-nocsd) | 14 | 30 of 30 alive; with gtk-nocsd first the gjs programs export nothing, as known (UNITY-20261013-013), which is why 52 puts ours first |
| T6 cold sessions: B (`~/.xsessionrc` libm), C (gtk-nocsd turned off), F (ours bare in `~/.xsessionrc`), A (none) | 15 | B: everything has `ours:nocsd:libm.so.6`, gnome-calculator and gnome-characters (gjs) export their menubar; C: `ours:libm.so.6`, both export; F: ours moved first, both export, and gnome-tweaks (PyGObject) too; A: as before |
| T7 removed (`dpkg -r --force-depends`, test machine only), conffile kept, cold sessions | 15 | R (libm): no entry of ours anywhere, no menubar, no "cannot be preloaded" for ours (the one line is ssh-agent refusing the user's bare `libm.so.6`); R2 (none): no entry of ours, 0 such lines; reinstalled after |

Debugging T2 used a build of the same source with two extra log lines in `late_mapped` and `on_owner_gone`, preloaded
for one papers run from `/usr/lib/x86_64-linux-gnu/libugm-debug.so.0`. Papers' AppArmor profile refuses a library in
the home directory. The file was removed afterwards. It is not part of the package or of any log above except the
explanation here.

One addition beyond DESIGN, for the Verifier: the current owner's `destroy` signal schedules a relook as its `unmap`
does. An owner destroyed while already hidden (no unmap then) and without a later `items-changed` would otherwise
never trigger one.

## Verifier (2026-10-17): PASS, REVIEWED

An independent Verifier (a subagent following `.claude/agents/adversarial-verifier.md`) reviewed the diff
`d377096..e308fc5`, DESIGN.md, the logs, the -039 card and the built deb. It reproduced nothing itself.

What it checked and found holding:
- every artifact hash and the source tree hash;
- the conffile, byte for byte;
- all seven rows of the switch rule against `relook_idle`;
- the relook filter;
- every lifetime path, including the destroy handler during dispose and both idles;
- `proxy_for`/`proxy_free`;
- the extra owner `destroy` trigger (sound);
- part B (equivalent to 0.13 for every result);
- part C (guard, opt-outs, `[ -e ]`, the quoted STARTUP pattern, variable cleanup, `set -e` safety);
- every row of the results table against its log.

Findings, all non-blocking (test quality, not the code):
1. **Test 28 does not exercise the compare-then-clear in `proxy_free` (round-2 #4).** Its two pages have different
   holders, so 0.13's unconditional clear would pass it too. The case that needs the check (the same holder, another
   owner) does happen in log 11 (Console's window-class actions) and is correct by inspection
   (`src/unity-gtk4-menu.c`:775-780), but no test pins it. The property-action mirror DESIGN lists under test 28 is
   not tested either. **Correction to DESIGN's round-2 table:** test 28 does not cover finding 4.
2. **Test 24:** the second `wait_log_n("relook", 2)` returns at once (substring count), and its "shown=1 primary=0"
   check is satisfied by the realize log. The case's claim still rests on "relook: the menu followed is kept".
3. **Test 27(c)** checks a message that both the window destroy handler and `rebuild_idle` print. Here it can only
   come from the former.

Notes:
- **Map filter.** A realize-time owner outside a header bar comes back only through C's unmap or destroy, as DESIGN
  says.
- **Stale rank.** `rec->primary` is not refreshed on a rebuild, as in 0.13.
- **Class references.** `patch_map` takes a class reference per fill, which is harmless.
- **T4.** It has no Pinta run and no 0.13 survey comparison. Late fill is covered by latetest 1-22.
- **Log headers.** Log 12b's header prints the installed version (0.14) above the line that says 0.13 was
  preloaded. Log 15's R/R2 headers print 0.14 for a package in `rc` state.

The test findings go to a follow-up task (ID from C). They need a change in the package's tests, so a new source commit.
