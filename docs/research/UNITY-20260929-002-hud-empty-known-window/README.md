# UNITY-20260929-002: the HUD is empty although the window is known

Owner: agent B (target2). Follow-up of UNITY-20260927-029 (mechanism 2).
With hud +unity2 and +unity3 the LibreOffice Writer window is always in
the window stack, yet on the first Writer start after a boot the HUD
answers nothing (2026-10-02: 1 of 20, 1 of 10, 1 of 10 and 1 of 10, each
time run 1 of the session; -029 logs/07 and /12, -028 logs/04 and /07).

```yaml
task_id: UNITY-20260929-002
package: hud
target_series: resolute
issue: local - legacy B-L45 follow-up, mechanism 2 of UNITY-20260927-029
status: INVESTIGATING
source_version: 14.10+17.10.20170619-0ubuntu6+unity3 (published 2026-10-02)
binary_version: hud 14.10+17.10.20170619-0ubuntu6+unity3 on target2
observed: >
  see logs/01 (reproduction); the lead from the -029 card: in one such
  boot hud-service logged DBusMenuImporter "no interface
  com.canonical.dbusmenu on /org/ayatana/bamf/window/...", and
  window-stack-bridge saw org.ayatana.bamf change owner.
expected: >
  the first LibreOffice start after a boot gets its menus in the HUD like
  every later one.
```

## Reading the code (hud +unity3, service/ and window-stack-bridge/)

Facts from the source, before any measurement:

- `ApplicationListImpl::WindowCreated` (the bridge's signal, sent when bamf
  announces the window) calls `ensureApplicationWithWindow`, which calls
  `ApplicationImpl::addWindow`, which creates the `WindowImpl` once per
  window id (`m_windows[windowId]`, `ApplicationImpl.cpp:49-55`).
- `WindowImpl`'s constructor creates its two collectors at once
  (`WindowImpl.cpp:81-82`), and `WindowImpl::activate` only reuses them.
- `GMenuWindowCollector` reads the six `_GTK_*`/`_UNITY_OBJECT_PATH`
  window properties once, in its constructor, through
  `GetWindowProperties`; with an empty `_GTK_UNIQUE_BUS_NAME` it stays
  invalid for the life of the window (`GMenuWindowCollector.cpp:42-63`).
  Nothing watches the properties afterwards.
- `DBusMenuWindowCollector` asks the bridge `GetWindowBusAddress`, which
  returns the bamf window's own D-Bus service and path
  (`BamfWindowStack.cpp:252-261`), and builds a `DBusMenuCollector` on it;
  so the "no interface com.canonical.dbusmenu on /org/ayatana/bamf/window"
  message is what that collector prints when activated, for any window.
  It also asks the AppMenu registrar `GetMenuForWindow` and listens to
  `WindowRegistered` for later registrations; LibreOffice's gtk3 VCL does
  not use the registrar, it exports GMenus and sets the `_GTK_*`
  properties.

- The GMenu path, when the properties are there: `GMenuCollector` owns a
  `QtGMenuImporter`; `activate()` hands out one `CollectorToken` per
  `QMenu` object and keeps it while the `QMenu` is the same
  (`GMenuCollector.cpp:46-58`). `WindowTokenImpl` indexes every token's
  `QMenu` once, in its constructor (`ItemStore::indexMenu`,
  `WindowImpl.cpp:31-34`); `ItemStore::search` runs over that index
  (`ItemStore.cpp:174-194`). A later `items-changed` from the model adds
  `QAction`s to the `QMenu` (`QtGMenuModel::ChangeMenuItems`) and reaches
  `CollectorToken::changed` -> `WindowTokenImpl::childChanged` -> a timer
  -> `changed()` -> `QueryImpl::refresh`, which only re-runs the search on
  the old index (`QueryImpl.cpp:192-205`). Nothing re-indexes. A new
  `StartQuery` calls `WindowImpl::activate` again, which finds the same
  tokens and keeps the same `WindowToken` (`WindowImpl.cpp:104-113`).
- LibreOffice's gtk3 VCL (26.2, `vcl/unx/gtk3/gtkframe.cxx:563-623`,
  `attach_menu_model`, called from `GtkSalFrame::Init` at :1794): the
  `_GTK_*` properties and an **empty** exported menu model exist from frame
  creation, before the window is shown; the model is filled only when the
  menubar is attached (`GtkSalMenu::SetFrame`, `gtksalmenu.cxx:1012-1052`,
  `g_lo_menu_insert_section` at :1051), which emits `items-changed`.

## Existing-fix discovery (subagent, read-only; 20 minutes)

- No later or forked hud changes this: lp:hud ended with the 2017 release;
  the later Launchpad branches and the archive's 0ubuntu4-6 are packaging
  and build changes; hud was never in Debian; UBports/Lomiri dropped the
  HUD; the Ubuntu Unity remix carries no patched hud that could be found
  (its PPA was not reached: UNKNOWN).
- Bugs: LP #1771173 (symptom only, New); LP #1045353 (2012, "LibreOffice
  commands are not displayed in the HUD", fixed on the LibreOffice side in
  13.10, an action-activation fix); LP #1288025 / #1278720 (2014, fixed in
  hud 13.10.1+14.04.20140314: several GMenu collectors per window, still a
  one-shot read). No bug describes menus that appear after the window.
- The sibling in the same desktop: indicator-appmenu
  (`src/indicator-appmenu.c`, `ensure_menus()` from
  `update_active_window()`) reads the `_GTK_*` properties lazily at every
  focus change and does not cache a miss; it watches no X property.

## Reproduction, round 1 (logs/01, cold-boot loop on the published +unity3)

Boot 1 (first Writer start after the rollback) in bamf's own words
(bamfwatch): at 10.56 s window 54525988 opens under a temporary
application with no desktop file (the -029 race, tolerated); at 10.77 the
application becomes libreoffice-writer; at **15.35 s a second window,
54526746, opens under libreoffice-writer and takes the focus** (the window
stack lists 54525988 as not focused and 54526746 as focused). `lo7.sh`
had picked 54525988 as "the Writer window" (the last visible window whose
name contains "LibreOffice Writer") and queried the HUD while 54526746
had the focus: the HUD serves the focused window.

HYPOTHESIS B, to measure next: the second window is LibreOffice's
first-start dialog ("Tip of the Day", shown once per day, so once after
every profile reset and once after the first boot of a day); it has no
menus, so the HUD is empty while it has the focus. This would also
explain the -029 logs/06 boot 4 pattern (answered, then empty 5 s later:
the dialog came up between the two queries) and the lone archive-hud case
of the -029 card (xid 56623243, no application id). If so, mechanism 2 is
not a hud defect but the dialog's focus, and the measurement scripts
mis-chose the window.

Round 1 result (logs/01): **3 of 10** cold boots empty at the first query
(boots 1, 4, 5); boot 5 answered at the second query 5 s later. In boots
4 and 5 the window stack holds one LibreOffice window, focused, so
hypothesis B (a dialog has the focus) does not explain them; boot 1 did
have a second, focused window (54526746). The splash window (60817409,
"LibreOffice 26.2", class soffice) opens about 1 s after the start and
closes when the document window appears, 7-18 s later; the failing boots
are not the slowest ones (boot 6, 15.5 s, passed).

Correction to the code reading: `QtGMenuModel::GetQMenu` builds a new
`QMenu` on every call (`QtGMenuModel.cpp:157-164`), so every `StartQuery`
gets a new token and a fresh index (`GMenuCollector::activate`,
`WindowImpl::activate`). The HUD is therefore empty at a query when the
imported model has no (enabled) items *at that moment*, not because of a
stale index. Hypothesis A, restated: in the failing boots LibreOffice's
exported menu model is still empty 8 s after the window is visible (and
13 s in boot 4), and filled by 13 s in boot 5; what delays the export
(the Registrar name watch, `UpdateFull`, or the action group) is the
measurement of round 2 (logs/02: the D-Bus order of WindowCreated, the
Start subscription and its reply, the Changed signals, and the query).

Round 2 (logs/02, `coldloop3.sh` with `menutrace.sh` and `lowindows.sh`),
**stopped after 6 of 10 boots** (2026-10-03, all agents stopped by May):
boot 6 was empty at the first query and answered at the second (4 hits);
boots 1-5 answered both. The D-Bus captures (`boot-N.raw`, with the
WindowCreated / Start / Changed order) are saved but **not analysed yet**.
Next step on resume: compare the order in boot 6 against boots 1-5, then
boots 7-10.

### Round 2, analysed (2026-10-08; `round2.py`, `hudsub.py`)

The captures record method calls and signals of `org.gtk.Menus`, the
window stack and `com.canonical.hud`, but no method returns, so the
unique bus name of hud-service is not known from them.

- In all 6 boots the window stack gives the Writer window the window
  number as application id (the UNITY-20260927-029 fallback), the failing
  boot 6 included. It does not tell boot 6 apart.
- Two clients subscribe to LibreOffice's menubar after WindowCreated, each
  with 82 `org.gtk.Menus` Start calls (the menubar and every submenu
  group); one of them is hud-service, the other INFERENCE the panel's
  appmenu. LibreOffice's first `Changed` comes 1.4-3.5 s after the first
  Start.
- **Boots 1-5:** both walks end 5.0-6.7 s before the HUD query.
- **Boot 6 (empty first answer):** both walks were still running at the
  query; their last Start calls are 2.65 and 2.87 s after it, and the walk
  took about 15 s instead of about 5. The second query a few seconds later
  answered (4 hits).

So in boot 6 the query reached hud-service while it was still importing
the menu; the answer is a snapshot of what had arrived. The code says the
open query should then fill in by itself: `QueryImpl::refresh` calls
`Window::activate` each time, which builds new tokens and a new index from
the current `QMenu` (`GMenuCollector::activate`, `QtGMenuModel::GetQMenu`),
and a token's `changed()` (from `items-changed`) calls `refresh`
(`QueryImpl.cpp:190-205`). Whether it does, and what a user sees in the HUD
during the import, is not measured: menutrace read only the reply of
`StartQuery`.

Next, round 3: record the unique names of hud-service and
unity-panel-service; query the HUD as soon as the Writer window is
visible (to land inside the import on purpose), keep that query open and
read its results again at +1, +2, +5 and +10 s (changing the query text
through `UpdateQuery` and back), and log hud-service's walk with the times.

Two facts found while preparing round 3 (2026-10-08):

- hud-service is D-Bus activated by compiz about one minute after the
  session starts (the user journal of the 11 earlier boots: "Activating
  via systemd: service name='com.canonical.hud' ... comm=/usr/bin/compiz"),
  so it runs before Writer is started. In the session restored from a
  saved state on 2026-10-08 it had not been started at all until the first
  query activated it; that first query (legacy `StartQuery`, 4.3 s while
  the service came up) returned 0 suggestions.
- target2 for round 3 is not the round 1-2 state: UNITY-20261008-001
  installed the GTK4/GTK3 applications of its audit, dev packages, gdb and
  dotnet-sdk-10.0, and unattended-upgrades updated archive packages
  (LibreOffice among them) on 2026-10-08.

HYPOTHESIS A, original wording, kept for the record: on the first Writer start after a boot the window
is mapped, and bamf announces it, before LibreOffice attaches the menubar;
hud-service subscribes to a model with no items, indexes nothing, and the
`Changed` that follows never makes it re-index, so the HUD stays empty
for that window. On later starts the menubar is attached before bamf
announces the window. The earlier guess (properties missing at
`WindowCreated`) is dropped: LibreOffice sets them at frame creation.

## Round 3 (logs/03, 2026-10-08)

**Where it ran.** target2 rolled back to Clean-2 (checked inside: no
`~/.dirty`, no work directories, archive hud, LibreOffice 26.2.5.2), then
our repository by a user's `full-upgrade` (hud `+unity3`, gtk-nocsd
`4.8-1+unity3`, unity `+unity12`, bamfdaemon 0.5.6+22.04.20220217-0ubuntu6;
the archive's updates brought LibreOffice 26.2.6.3) plus `xdotool`, nothing
else. A first round 3 on the state left by UNITY-20261008-001 stopped when
target2 hit a Guru Meditation on the reboot after its boot 1 (about
05:18Z); its one boot is kept apart in `logs/03-livequery-dirty` and not
counted.

**Method** (`coldloop4.sh`, `livequery.py`): 10 cold boots; Writer started
as `lo7.sh` starts it; the HUD queried **as soon as the Writer window is
visible**, the way Unity's HUD client does (`CreateQuery`, results in a Dee
shared model); the live results model read at +0, +1, +2, +5, +10, +20 s,
with `UpdateQuery` to another text and back at +12 s. Also one legacy
`StartQuery` at +0.

| | boots |
|---|---|
| empty at +0 (legacy `StartQuery` and live model) | 10 of 10 |
| the open query fills in by itself (5 results with Файл) | 8 of 10: at +2 s in 1 boot, at +5 s in 7 |
| still empty at +20 s, also after `UpdateQuery` | 2 of 10 (boots 1 and 2) |

**Boots 1 and 2:** a second LibreOffice window opened 3.6-5.0 s after the
document window, under the application libreoffice-writer, and took the
focus (window stack: the document window `false`, the new one `true`);
the HUD answers for the focused window. That second window is LibreOffice's
**"Tip of the Day" dialog**: with `LastTipOfTheDayShown` set back from
20734 (2026-10-08) to 20700, a Writer start shows "Совет дня: 1/224",
focused (vbox screenshot); the HUD answers 0 while it has the focus and 4
after OK closes it (`logs/04-tipoftheday.txt`). It came back in boot 2
because the profile change of boot 1 was not written before the reboot
(INFERENCE: LibreOffice was killed by the reboot).

## Result

The symptom of this task, "the HUD is empty although the window is
known, on the first Writer start after a boot", has two causes, and
neither is a hud defect:

1. **The Tip of the Day dialog has the focus.** On the first start of a
   day (and after a profile reset) LibreOffice shows it a few seconds after
   the document window. The HUD searches the focused window, the dialog has
   no menu, so the answer is empty; it is right again once the dialog is
   closed. Our measurement scripts (`lo4.sh`, `lo7.sh`) chose the window by
   its title, not by the focus, and so counted these runs as "the window is
   known, the HUD is empty". This also fits the -029 logs/06 boot 4
   (answered, then empty 5 s later: the dialog came up between the two
   queries) and round 1 boot 1 here (a second focused window).
2. **A query in the first seconds after the window appears** comes while
   hud-service is still importing the window's menu over `org.gtk.Menus`
   (round 2: about 82 Start calls, usually done within about 5 s, once
   about 15 s; round 1 boot 4, with one LibreOffice window, was empty at
   both queries, about 8 and 13 s after the window appeared). The answer is
   what has arrived so far; an open query fills in by itself when the rest
   arrives (round 3: 8 of 8 boots without the dialog, by +2 to +5 s), as
   the code says (`QueryImpl::refresh` on the token's `changed`). A HUD
   opened in those seconds shows no results at first and then shows them,
   without being reopened. Why the import sometimes takes about 15 s
   (LibreOffice answering slowly on its first start, or the two clients
   walking at once) was not measured.

Proposed terminal state: NOT_APPLICABLE (correct behaviour, measured);
the decision is the coordinator's. No code is proposed. The window-number
application id (UNITY-20260929-001) was present in all boots and is not a
factor here.
