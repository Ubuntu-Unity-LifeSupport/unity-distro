# Unity panel: the first start of a GTK4 application ignores its Alt mnemonic (UNITY-20261012-003)

Owner: agent B (target2).

```yaml
task: UNITY-20261012-003
title: the first start of a GTK4 application in a session ignores its Alt mnemonic until the window is focused again
found_in: UNITY-20261012-001 logs/03-mnemonics-keys.txt (gtk-nocsd builds preloaded alone, real keys)
target_series: resolute
status: NOT_REPRODUCED on the live stack (sessions 5-7, measured by events, 2026-10-13)
```

## Where it was seen (UNITY-20261012-001)

UNITY-20261012-001 tested mnemonics with real keys. Each application was preloaded with one gtk-nocsd build
alone. In those tests the first start of an application in a session did not open its menu:

- Pinta with `fd4b76a`: nothing on the first Alt+F, and the HUD on the second;
- GNOME Text Editor with `fd4b76a`: Alt+F10 did nothing twice, and the holder menu opened after a minimise and
  activate;
- Pinta with `2d50fe9`, in a new session: nothing on one press, no refocus tried.

Later starts of the same application in the same session opened the menu at once. The exported menus of the first
starts were correct (`audit.py`).

## Rig

- `setup.sh`: confirm the Clean-2 restore inside the guest, add the live archive, full-upgrade, then install
  libunity-gtk4-menu0 (UNITY-20260927-037), the tools and GTK4 applications from the archive.
- `start.sh TAG APP`: the user's view of the live stack. It starts APP in the session's environment (taken from
  compiz, with the session's own `LD_PRELOAD`) and focuses the window. It then prints the window's `_GTK_*`
  properties and the exported menu (`audit.py`, from research/nocsd-gaps). `NOAUDIT=1` skips `audit.py`, which
  subscribes to the menu itself.
  - Before the start, a `dbus-monitor` records every `org.gtk.Menus` and `org.gtk.Actions` call on the session
    bus. The monitor runs until `stop.sh TAG`.
- `stop.sh TAG`: ends the monitor and prints the calls, with bus names mapped to processes. That shows whether
  and when the panel subscribes.
- Keys come from the host (vbox `send_keys`, scancodes). Sessions 1-3 judged outcomes from vbox screenshots;
  from session 4 on, from events (`popwatch.sh`, `ShowEntry`, `EntryActivated`). Each session is a
  cold boot: poweroff over ssh, then `start_vm`.
- `sync.sh`: the panel service's own entry table (`com.canonical.Unity.Panel.Service.Sync`): the label, sensitive
  and visible flags, and the parent window of every application-menu entry, together with the active window.
- `popwatch.sh`: polls unity-panel-service's visible windows (its menu popups) every 50 ms, which gives the time the
  popup is mapped.
- `mnemo.py`: a GTK4 application with its own menubar `_File`, `_Edit`, `_Help`. Alt+F can be typed on the
  guest's gb/us layouts. The holder labels of Calculator and Text Editor carry no underscore.
- `trial.sh begin|end`: one counted attempt. It prints the versions, runs `start.sh` with `NOAUDIT=1`, then
  `sync.sh` and `popwatch.sh`. Exactly one key comes from the host. After Escape, the unmap is confirmed before the
  next attempt.

## Where it ran

target2 was restored to Clean-2 and confirmed inside, then set up with `setup.sh` (logs/01). The live archive was
unity-resolute-20261009-003 (Release Date 2026-10-12 23:18:38 UTC). After the full-upgrade, every session ran the
same packages:
- libunity-gtk4-menu0 0.9;
- libgtk-nocsd0 4.8-1+unity3;
- unity 7.7.1+26.04.20260306-0ubuntu3+unity13;
- indicator-appmenu 15.02.0+20.10.20260311-0ubuntu1;
- bamfdaemon 0.5.6+22.04.20220217-0ubuntu6.

The session preloads `libunity-gtk4-menu.so.0:libgtk-nocsd.so.0`. Each session is a cold boot. Live moved on to
-20261012-005 at 00:08:28Z (gtk-nocsd +unity4, UNITY-20261012-005), but apt did not run on target2 after the setup,
so the series ran on the versions above.

## Results

### Sessions 1-4: exploratory (logs/02, logs/03)

Session 1 seemed to reproduce the bug:
- Text Editor's first start opened its menu at once;
- Calculator's first start showed nothing after two Alt+F10 presses, and opened after a minimise and activate.

That was a measurement error. The outcome was judged from a vbox screenshot taken right after the key, and the
screenshot came before the popup was mapped:
- In session 3, a screenshot 15 s after the key shows Calculator's menu open.
- In session 4, `popwatch.sh` measured it: compiz `ShowEntry` at 00:33:51.684, `EntryActivated` at 52.351, and the
  popup mapped at 52.604, 0.92 s after `ShowEntry`.
- In session 1 the second Alt+F10 came 4 s after the first, so it most likely closed a menu that had opened by then.

Seen in every session, before any key:
- The panel service already has the window's entry: label, sensitive, visible, with the right parent window.
- compiz has already fetched it (`ReSync` → `SyncOne libappmenu.so`).
- unity-panel-service subscribes to the window's menu (`org.gtk.Menus.Start`) 0.1-0.2 s after the window becomes
  active.

Nothing waits for a focus change.

### Sessions 5-7: the counted series (logs/04)

Measured by events, not screenshots. Each row is the first start of that application in that cold session. The
latencies are from compiz's `ShowEntry`, which unity sends when it takes the key. "Popup mapped" is popwatch's
50 ms poll, about ±0.1 s.

| session | application, key | opened on the first press | → `EntryActivated` | → popup mapped |
|---|---|---|---|---|
| 5 | mnemo.py, Alt+F (`_File`) | yes | 47 ms | 0.15 s |
| 5 | Calculator, Alt+F10 | yes | 238 ms | 0.43 s |
| 5 | Text Editor, Alt+F10 | yes | 79 ms | 0.27 s |
| 6 | Calculator, Alt+F10 (first application of the session) | yes | 323 ms | 0.45 s |
| 6 | mnemo.py, Alt+F | yes | 64 ms | 0.24 s |
| 7 | mnemo.py, Alt+F (first application of the session) | yes | 167 ms | 0.29 s |
| 7 | Calculator, Alt+F10 | yes | 253 ms | 0.25 s |

Alt+F opened on the first press 3 of 3 times, and Alt+F10 4 of 4 (Calculator 3, Text Editor 1). Outside the count,
session 4 also opened on the first press: mnemo.py Alt+F (0.58 s) and Calculator Alt+F10 (0.92 s). Calculator's
first open is the slowest, 0.25-0.92 s. Text Editor and mnemo.py take 0.15-0.58 s.

## Outcome: NOT_REPRODUCED on the live stack

On our live stack, the first start of a GTK4 application in a session does not ignore its Alt mnemonic. Alt+F
(`MenuManager`'s mnemonic grab) and Alt+F10 (`PanelMenuView`) open the menu on the first press, within 0.15-0.92 s,
and need no refocus. The first open of Calculator's menu takes up to 0.92 s. That is recorded as a fact here, and
no task is opened for it.

UNITY-20261012-001's first-start observations (logs/03-mnemonics-keys.txt there) were judged the same way, from
screenshots after the key, with a second press a few seconds later. They ran gtk-nocsd `fd4b76a` and `2d50fe9`
preloaded alone, which we do not ship. Its Pinta case (nothing on the first Alt+F, the HUD on the second) is not
explained by a slow popup. That case was not retested here: on our packaged stack Pinta exports no menubar
(UNITY-20261012-001 logs/03-mnemonics-start.txt). The correction to that card is a new DECISIONS record. The card's
text stays as written.

## Existing-fix discovery (subagent, read-only, 2026-10-13)

- No newer unity, indicator-appmenu or bamf exists in any Ubuntu series:
  - unity 7.7.1+26.04.20260306-0ubuntu3, the same in resolute and stonking;
  - indicator-appmenu 15.02.0+20.10.20260311-0ubuntu1, the same in both;
  - bamf 0.5.6+22.04.20220217-0ubuntu6, the same in both.
- Debian ships only bamf (0.5.6+repack-2).
- The unity GitLab branch ubuntu/devel (newest commit 6f01ccb7, 2026-04-21) has no panel or menu change.
- No Launchpad bug matches this symptom. The nearest is LP #1025860, "alt+f+a doesn't work the first time round"
  (Triaged since 2012), which is about submenu mnemonics.
- Code reading for the record:
  - indicator-appmenu's `ensure_menus()` and unity's `MenuManager` mnemonic grab and `PanelMenuView::OnEntryAdded`
    resynchronise only on a focus change;
  - a window whose entries arrive before it becomes active could miss them.
  - The series above did not hit that, because the panel subscribes 0.1-0.2 s *after* the window becomes active.
- No newer release was needed, because nothing reproduced.
