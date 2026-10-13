# Unity panel: the first start of a GTK4 application ignores its Alt mnemonic (UNITY-20261012-003)

Owner: agent B (target2).

```yaml
task: UNITY-20261012-003
title: the first start of a GTK4 application in a session ignores its Alt mnemonic until the window is focused again
found_in: UNITY-20261012-001 logs/03-mnemonics-keys.txt (gtk-nocsd builds preloaded alone, real keys)
target_series: resolute
status: NOT_REPRODUCED on the live stack (sessions 5-10, 13 attempts measured by events, 2026-10-13)
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
- `trial.sh begin|end`: one counted attempt. It prints the package versions and boot time (the version of logs/04
  printed three packages and no boot time on its `==` line; the boot time is on its start lines). Then it runs `start.sh`,
  `sync.sh` and `popwatch.sh`. By default `start.sh` gets `NOAUDIT=1`. With `AUDIT=1`, audit.py subscribes to the
  menu between the focus and the key, which is the UNITY-20261012-001 rig's condition. Exactly one key comes from
  the host. After Escape, the unmap is confirmed before the next attempt.
- `table.py`: computes the results table from the trial logs: the active window, the panel's first `Start`, compiz's
  first `SyncOne libappmenu.so` after the activation,
  `ShowEntry`, `EntryActivated` and the popup map.

## Where it ran

target2 was restored to Clean-2 and confirmed inside, then set up with `setup.sh` (logs/01). The live archive's
Release fetched there is dated 2026-10-12 23:18:38 UTC. That is the Release of the unity-resolute-20261009-003
publication (research/UNITY-20261009-003-hud-unity7, Publication and logs/10). Every session ran the same
packages; the `==` lines of logs/04 and logs/05 print them:
- libunity-gtk4-menu0 0.9;
- libgtk-nocsd0 4.8-1+unity3;
- unity 7.7.1+26.04.20260306-0ubuntu3+unity13.

logs/05 also prints indicator-appmenu 15.02.0+20.10.20260311-0ubuntu1 and bamfdaemon 0.5.6+22.04.20220217-0ubuntu6,
as does logs/01. The version lines are the record of what ran; later publications do not appear in them. The session
preloads `libunity-gtk4-menu.so.0:libgtk-nocsd.so.0`, and each session is a cold boot.

## Results

### Sessions 1-4: exploratory (logs/02, logs/03)

Session 1 looked like a reproduction:
- Text Editor's first start opened its menu at once.
- Calculator's first start showed nothing after two Alt+F10 presses, 4 s apart, and opened after a minimise and
  activate.
- That Calculator start ran with audit.py; the Text Editor start ran without it.

Those outcomes were judged from vbox screenshots taken right after the key. Session 3 showed that such a screenshot
can come before the popup is mapped, and session 4 timed the map:
- **Session 3:** the screenshot right after the key shows nothing. A screenshot 15 s later (00:29:29Z, after
  `ShowEntry` at 00:29:14.147 and `EntryActivated` at 14.441) shows Calculator's menu open. This is logs/03's text;
  the screenshots are not in the repository.
- **Session 4:** `popwatch.sh` timed it: `ShowEntry` at 00:33:51.684, `EntryActivated` at 52.351, and the popup
  mapped at 52.604, 0.92 s after `ShowEntry`. Session 4's start lines (versions, boot) are not in logs/03.

So **for session 1 it is an inference, not a measurement**, that the key was taken and the second press closed a
menu that had opened by then. Session 1 has no `ShowEntry`, `EntryActivated` or popup timing. Its Calculator
condition, audit.py running with the first start, was measured by events later (sessions 8-10, below).

Before the key, the panel service's entry table (`sync.sh`) was logged in sessions 3 and 5-10. Each time it
already held the window's entry, with its label, sensitive and visible flags and the right parent window.
Sessions 1, 2 and 4 have no such table in the logs. Sessions 3-10 show compiz fetching the entries
(`ReSync` → `SyncOne libappmenu.so`). Sessions 1 and 2 show no such lines; the monitor of that time had no match rule for the panel service's interface
(added to `start.sh` before session 3).

### Sessions 5-10: the counted series (logs/04, logs/05)

Measured by events, not screenshots. Each row is the first start of that application in that cold session, and in
each attempt there is exactly one `ShowEntry` and one non-empty `EntryActivated`. The latencies are from compiz's
`ShowEntry`, which unity sends when it takes the key.

"Popup first" is the first popwatch line with a visible window of unity-panel-service; "popup full" is the line
where the count reaches its maximum (2). popwatch sleeps 50 ms between polls, and each poll runs two `xdotool` calls; the real period was not measured
(estimated ±0.1 s). The last column is the time from
the window becoming active (`_NET_ACTIVE_WINDOW`) to unity-panel-service's first `org.gtk.Menus.Start` to it.
Everything is computed by `table.py` from the logs.

| session | application, key | audit.py | opened on the first press | → `EntryActivated` | → popup first / full | active → panel `Start` |
|---|---|---|---|---|---|---|
| 5 | mnemo.py, Alt+F (`_File`, first application) | no | yes | 47 ms | 0.15 / 0.15 s | 0.18 s |
| 5 | Calculator, Alt+F10 | no | yes | 238 ms | 0.43 / 0.43 s | 0.16 s |
| 5 | Text Editor, Alt+F10 | no | yes | 79 ms | 0.27 / 0.27 s | 0.21 s |
| 6 | Calculator, Alt+F10 (first application of the session) | no | yes | 323 ms | 0.45 / 0.62 s | 0.22 s |
| 6 | mnemo.py, Alt+F | no | yes | 64 ms | 0.24 / 0.24 s | 0.54 s |
| 7 | mnemo.py, Alt+F (first application) | no | yes | 167 ms | 0.29 / 0.50 s | 0.32 s |
| 7 | Calculator, Alt+F10 | no | yes | 253 ms | 0.25 / 0.47 s | 0.40 s |
| 8 | Calculator, Alt+F10 (first application) | yes | yes | 242 ms | 0.28 / 0.48 s | 0.20 s |
| 8 | mnemo.py, Alt+F | yes | yes | 66 ms | 0.42 / 0.42 s | 0.28 s |
| 9 | mnemo.py, Alt+F (first application) | yes | yes | 54 ms | 0.27 / 0.27 s | 0.27 s |
| 9 | Calculator, Alt+F10 | yes | yes | 175 ms | 0.29 / 0.29 s | 0.14 s |
| 10 | Calculator, Alt+F10 (first application) | yes | yes | 198 ms | 0.47 / 0.47 s | 0.26 s |
| 10 | Text Editor, Alt+F10 | yes | yes | 83 ms | 0.26 / 0.26 s | 0.34 s |

Totals: Alt+F opened on the first press 5 of 5 times. Alt+F10 opened 8 of 8 times: Calculator 6, Text Editor 2.
That includes 6 of 6 with audit.py running. The two uncounted session 4 attempts also opened on the first press
(mnemo.py Alt+F, popup at 0.58 s; Calculator Alt+F10, 0.92 s).

- **Latency:** in the counted series, `ShowEntry` → `EntryActivated` is 175-323 ms for Calculator and 47-167 ms for
  the other two applications; 667 ms for Calculator in session 4. Calculator's popup is not always the last to map
  (session 7: Calculator 0.25 s, mnemo.py 0.29 s).
- **Panel subscription:** the panel service subscribes to the menu (`org.gtk.Menus.Start`) 0.14-0.54 s after the
  window becomes active, never before. compiz takes the entries (`SyncOne libappmenu.so`) 0.38-1.60 s after the
  activation.
- **Contents:** "opened" means the popup was mapped and `EntryActivated` named the application's entry: `_File`
  for mnemo.py, the holder for the others. No other indicator entry was activated within any attempt. The contents
  were checked by eye once per application in session 8: a vbox screenshot after the map shows Calculator's holder
  with its underlined letters, and mnemo.py's File menu (New, Open, Quit).
- **Focus:** `start.sh` runs `xdotool windowactivate` on a window that is already active, as the UNITY-20261012-001
  rig did. The `_NET_ACTIVE_WINDOW` log shows no second change.

**Limits:**
- 13 counted attempts, Text Editor only twice.
- Alt+letter on the Calculator and Text Editor holders is not tested: their labels have no underscore, and the
  guest layouts cannot type Cyrillic.
- "First start" means the first start of that application in the trial order of a cold session. Nothing else was
  started in between, but no log shows that.

## Outcome: NOT_REPRODUCED on the live stack

On our live stack, the first start of a GTK4 application in a session does not ignore its Alt mnemonic. Under the
conditions above, Alt+F (`MenuManager`'s mnemonic grab) and Alt+F10 (`PanelMenuView`) opened the menu on the first
press in 13 of 13 counted attempts, with and without audit.py, and needed no refocus. The popup maps 0.15-0.62 s
after `ShowEntry` in the series, and 0.92 s once, in session 4. That latency is recorded here as a fact; no task
is opened for it.

UNITY-20261012-001's first-start observations (logs/03-mnemonics-keys.txt there) were judged the same way, from
screenshots after the key:
- **Text Editor:** the second press came 6 s after the first, so the same timing explanation is possible. It was
  not measured there.
- **Pinta:** the second Alt+F came 20 s later and brought up the HUD. A slow popup does not explain that.

Those runs used gtk-nocsd `fd4b76a` and `2d50fe9` preloaded alone, which we do not ship. They were not retested
here; on our packaged stack Pinta exports no menubar (UNITY-20261012-001 logs/03-mnemonics-start.txt). The
correction to that card is a new DECISIONS record, and the card's text stays as written.

## Existing-fix discovery (subagent, read-only, 2026-10-13)

Searched against the sources linked below, not reproduced in a log here.

- **Newer versions:** none in any Ubuntu series, from Launchpad's published sources:
  - unity 7.7.1+26.04.20260306-0ubuntu3, the same in resolute and stonking;
  - indicator-appmenu 15.02.0+20.10.20260311-0ubuntu1, the same in both;
  - bamf 0.5.6+22.04.20220217-0ubuntu6, the same in both.
  - Debian ships only bamf, 0.5.6+repack-2 ([madison](https://qa.debian.org/madison.php?package=bamf)).
- **Upstream changes:** unity's GitLab branch ubuntu/devel has no panel or menu change; its newest commit is
  6f01ccb7 of 2026-04-21 ([commits](https://gitlab.com/ubuntu-unity/unity/unity/-/commits/ubuntu/devel)).
- **Bug reports:** no Launchpad bug matches. The nearest:
  - [LP #1025860](https://bugs.launchpad.net/bugs/1025860), "alt+f+a doesn't work the first time round", is about
    submenu mnemonics and has been Triaged since 2012;
  - [LP #734880](https://bugs.launchpad.net/bugs/734880) is an older menubar-refresh bug, Fix Released.
- **Code reading,** for the record. The subagent read these trees: indicator-appmenu 15.02.0+20.10.20260311 and
  the unity Launchpad tree, 7.7.0, whose panel files 7.7.1 leaves unchanged per the GitLab compare.
  - indicator-appmenu reads a window's `_GTK_UNIQUE_BUS_NAME` once, in `ensure_menus()`
    (`src/indicator-appmenu.c:1058-1091`). It retries only on `active-window-changed` (`:1095`).
  - unity's `MenuManager` grabs mnemonics when an entry is added only if the entry's window is compiz's active
    window (`unity-shared/MenuManager.cpp:145-147`); otherwise only on a focus change (`:78`, `:133`).
  - `PanelMenuView::OnEntryAdded` keeps entries only for its active window (`panel/PanelMenuView.cpp:950`).
  - So entries that arrive *before* their window becomes active could be missed until a focus change. In this
    series unity took them always after: compiz's first `SyncOne libappmenu.so` came 0.38-1.60 s after the window
    became active (`table.py`; the panel service's `ReSync` before it, 0.27 s at the earliest).
- **Newer release:** not needed, because nothing reproduced.

## Verification (independent Verifier, 2026-10-13): PASS in round 3

- **Round 1: FAIL.** The counted series held, and every latency matched the logs. Three blocking points in the
  text:
  - the active → panel `Start` delay was given as 0.1-0.2 s, but it is 0.14-0.54 s;
  - the entry-table claim covered sessions without such a table;
  - session 1 was called a measurement error, though that is an inference, and the audit.py condition was not
    measured by events.
  - Fixed: sessions 8-10 measured the audit.py condition (logs/05, 6 of 6), and the text was reworded.
- **Round 2: FAIL.** One point: the existing-fix section gave the panel service's subscription delay as the time
  unity takes the entries.
  - Fixed: compiz's `SyncOne libappmenu.so` comes 0.38-1.60 s after the activation, and `table.py` prints it.
- **Round 3: PASS.**
  - `table.py` was re-run, and a separate parser found no libappmenu `SyncOne` or `ReSync` before the
    activation in any of the 13 attempts.
  - Remark: `SyncOne` is compiz's request, and the entries arrive in its reply, so the time is a lower bound.
    That leaves "always after the activation" unaffected.
