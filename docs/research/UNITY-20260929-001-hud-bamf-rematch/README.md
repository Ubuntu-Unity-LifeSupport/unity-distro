# UNITY-20260929-001: window-stack-bridge keeps the window number as LibreOffice's application id

Owner: agent B (target2). Follow-up of UNITY-20260927-029. Since hud
`+unity2` window-stack-bridge keeps a window whose first application is
gone, with the window number as application id (the fallback the bridge
already had for an application without a desktop file). For LibreOffice
that is now the usual case: bamf announces the Writer window under a
temporary application and re-matches it to libreoffice-writer a moment
later, and the bridge never looks again.

```yaml
task_id: UNITY-20260929-001
package: hud (window-stack-bridge)
target_series: resolute
issue: local - follow-up of UNITY-20260927-029
status: INVESTIGATING
source_version: 14.10+17.10.20170619-0ubuntu6+unity3 (published 2026-10-02)
observed: >
  The window stack lists the LibreOffice Writer document window with its
  window number as application id: 19 of 20 starts in -029 logs/05, 10 of
  10 cold boots in UNITY-20260929-002 round 3 (2026-10-08, Clean-2 + the
  published stack). The Tip of the Day dialog, opened later under the
  already re-matched application, gets libreoffice-writer.
expected: >
  every window of an application gets that application's id
  (libreoffice-writer), as the dialog does.
```

## Reading the code (hud +unity3)

- `BamfWindow::BamfWindow` (window-stack-bridge/BamfWindowStack.cpp:28-75)
  computes the application id once: the first entry of the window's
  `Parents()`, then that application's `DesktopFile()` base name; with no
  parent, an empty desktop file, or (since +unity2) a failed
  `DesktopFile()` call, the window number.
- `BamfWindowStack::ViewOpened` (:284-291) creates the window and emits
  `WindowCreated(windowId, applicationId)`; `ViewClosed` emits
  `WindowDestroyed`; `ActiveWindowChanged` emits `FocusedWindowChanged`
  with the stored id; `GetWindowStack` returns the stored id. Only the
  matcher's `ViewOpened`, `ViewClosed` and `ActiveWindowChanged` are
  connected (:150-160). Nothing follows a window moving to another
  application.
- hud-service keys its applications by that id
  (`ApplicationListImpl::ensureApplication`, service/ApplicationListImpl.cpp:
  89-100; `WindowCreated` -> `ensureApplicationWithWindow`,
  `WindowDestroyed` -> `removeWindow`, which drops an application left
  without windows).
- bamf offers what is needed to follow it (data/org.ayatana.bamf.view.xml):
  on the application, `WindowAdded(path)` / `WindowRemoved(path)`,
  `Xids()`, `DesktopFile()`; on every view `ChildAdded` / `ChildRemoved`,
  `Parents()`, `Children()`; the matcher announces the new application
  with `ViewOpened(path, "application")` (the -029 bamfwatch logs: the
  temporary application closes and libreoffice-writer opens about 0.1-0.2
  s after the window).

Consequences named in the -029 card: the HUD shows no application icon and
name for such a window, and its usage history is kept under the window
number, so it starts empty at every LibreOffice start.

## Existing-fix discovery (subagent, read-only, 2026-10-08)

Sources: git.launchpad.net/bamf (HEAD 9183645, 0.5.7; our archive has
0.5.6, line numbers may differ), git.launchpad.net/unity (7.7.0+23.04),
git.launchpad.net/ubuntu/+source/indicator-appmenu
(15.02.0+20.10.20260311), git.launchpad.net/ubuntu/+source/hud
(0ubuntu6).

- **How bamf moves a window.** `handle_raw_window` connects
  "class-changed" to `on_raw_window_class_changed` (src/bamf-matcher.c
  l.2204): `bamf_view_remove_child(old_app, win)` (l.2229), register the
  new application if needed, `bamf_view_add_child(new_app, win)` (l.2236).
  The window object and its D-Bus path (`/org/ayatana/bamf/window/<xid>`)
  stay the same. On the bus: old application `ChildRemoved` +
  `WindowRemoved`; if it is now empty and closes, matcher
  `ViewClosed(old app)` and its `Closed`; if new, matcher
  `ViewOpened(new app, "application")`; new application `ChildAdded` +
  `WindowAdded`. **No `ViewOpened`/`ViewClosed` for the window itself**, so
  the bridge, which listens only to those, never sees the move. (The other
  re-match path, `bamf_legacy_window_reopen`, fakes a close and reopen of
  the window and is already handled by the bridge.)
- **libbamf:** no "parent changed" on a window; applications re-emit
  "window-added"/"window-removed"; `bamf_matcher_get_application_for_xid`
  answers the current application.
- **Unity 7** (`unity-shared/BamfApplicationManager.cpp`) connects every
  application's child-added/child-removed (l.367, l.380), and
  `AppWindow::application()` (l.242) asks bamf again on every call.
  **indicator-appmenu** does not track the move and looks the application
  up again on each use (`get_entries`, `ensure_menus`).
- **No later fix:** hud 0ubuntu1..0ubuntu6 changes are rebuilds and build
  fixes; no fork carries a change to window-stack-bridge. UNKNOWN: old bzr
  branches other than trunk, the upstream history of the bridge.

Existing fix: NOT_FIXED. Issue search: no report of this specific cause
found (the symptom of a missing HUD icon/name was not searched for
separately: UNKNOWN beyond LP #1771173, which is about an empty HUD).

## Reproduction (2026-10-08, logs/01, logs/02)

target2: Clean-2 + our repository by `full-upgrade` (hud `+unity3`, unity
`+unity12`, bamfdaemon 0.5.6+22.04.20220217-0ubuntu6, LibreOffice
26.2.6.3) + `xdotool` (set up by the UNITY-20260929-002 Verifier).
`repro.sh` starts Writer under a dbus-monitor capture of bamf and the
bridge.

The order on the bus for the document window 62914596 (logs/01):

| t (s) | sender | signal |
|---|---|---|
| .7890 | bamf | matcher `ViewOpened(window/62914596, window)` |
| .8070 | bamf | matcher `ViewOpened(application/0x…621950, application)`; that application `ChildAdded`/`WindowAdded(window/62914596)` |
| .8938 | bridge | `WindowCreated(62914596, "62914596")`, `FocusedWindowChanged(62914596, "62914596")` |
| .9020 | bamf | application/0x…621950 `ChildRemoved`/`WindowRemoved(window/62914596)`; matcher `ViewClosed(application/0x…621950)` |
| .9021 | bamf | matcher `ViewOpened(application/746707297, application)`; it `ChildAdded`/`WindowAdded(window/62914596)` |

The temporary application had no desktop file, so the bridge took the
window number; 8 ms after its `WindowCreated` bamf moved the window to
libreoffice-writer, and the bridge sent nothing more. Afterwards:

- the window stack: `(62914596, '62914596', true)`;
- bamf itself: `ApplicationForXid 62914596` -> application/746707297,
  `DesktopFile` `/usr/share/applications/libreoffice-writer.desktop`.

**What it changes for the user** (logs/02, vbox screenshots):

- The HUD on the panel shows the Writer icon even so: Unity takes the
  icon from bamf itself. The "no icon" of the -029 card is not seen here.
- **The usage history:** executing one HUD result (`CreateQuery`, the
  first result, `ExecuteCommand`, as Enter in the HUD does) recorded it in
  `~/.cache/indicator-appmenu/hud-usage-log.sqlite` as
  `('62914596', 'Файл||Сохранить')`. hud ranks results by that history per
  application id, and the next Writer window has another number (54525988,
  62914596, 65011748 in earlier boots), so Writer's HUD history is split by
  window number and mostly not found again. Where the history is used:
  `ItemStore::search` with an empty query (the HUD just opened, nothing
  typed) lists up to 20 items ordered by `usage(m_applicationId, entry)`
  (service/ItemStore.cpp:183-200), and `execute` marks the use under the
  same id (:295, :334). So for LibreOffice the "most used" list shown when
  the HUD opens does not learn across starts.

**How often** (logs/03, `freq.sh`: Writer or Calc started again and again
in one session, the previous instance killed; the window stack's id
against bamf's application and whether bamf moved the window):

| | window number as id | libreoffice-writer/-calc | bamf moved the window |
|---|---|---|---|
| Writer, 10 starts | 9 | 1 (start 1) | 9 (all but start 1) |
| Calc, 3 starts | 2 | 1 (start 3) | 3 |

Calc start 3 was moved and still got the right id: the bridge's
`Parents()` call was answered after the move. So the result is a race
between the bridge's two calls and bamf's re-match, which the bridge loses
most of the time; when bamf does not move the window (Writer start 1) the
id is right from the start.

Reproduction: PASS.

## Design (for the Design Challenger)

Invariant: **the bridge's application id for a window is the id of the
application bamf has the window under, also after bamf moves it.**

Facts the design rests on:

- bamf announces the move only with the applications' `ChildRemoved` /
  `ChildAdded` (and `WindowRemoved` / `WindowAdded`); the window's path
  stays the same.
- hud-service keys windows by application id; `WindowDestroyed(id, old)`
  removes the window and drops an application left empty, and if it was
  the focused application, sets the focus to none
  (`ApplicationListImpl::removeWindow`); `WindowCreated(id, new)` creates
  the window again (its collectors re-import the menu).

Candidates:

- **(A) Follow the children.** One QtDBus match for `ChildAdded` on
  `org.ayatana.bamf.view` from bamf on any path (the sender path is the
  application). For a known window path whose stored id differs from the
  new application's id (desktop file base name, or the window number if
  it has none): store the new id, emit `WindowDestroyed(xid, old)`,
  `WindowCreated(xid, new)`, and, if the window is bamf's active window,
  `FocusedWindowChanged(xid, new, MAIN)`. `GetWindowStack` and later
  `ActiveWindowChanged` then use the new id. This is Unity's own pattern
  (BamfApplicationManager follows child-added).
- **(B) Re-resolve lazily** (indicator-appmenu's pattern) in
  `GetWindowStack`/`ActiveWindowChanged`, and emit the same three signals
  when the answer differs. Simpler to wire, but the move is only noticed on
  the next focus change or stack query; hud-service's keyed state stays
  wrong until then.
- **(C) Wait before announcing:** hold `WindowCreated` of a window with a
  window-number id for some hundred milliseconds in case bamf moves it.
  Rejected: a timing guess, and still wrong when the move comes later.

Proposed: (A). To measure: the order of hud-service's own state after the
three signals (the HUD keeps answering for the window; the usage history
goes under libreoffice-writer); no extra windows or applications left
behind; other applications unchanged (a window that bamf never moves gets
no signal); bamf restarts.

### Design review, round 1: REVISE (all points taken)

1. **`WindowAdded` on `org.ayatana.bamf.application`, not `ChildAdded`**
   (which every view sends, tabs included). One QtDBus connection from
   `BAMF_DBUS_NAME` on any path (empty path); the match carries the
   sender, the test confirms only bamf's signals arrive.
2. **Resolve again from the window, keep the old id on error.** The
   `Parents()` -> `DesktopFile()` code becomes one resolver
   (`BamfWindow::resolveApplicationId`, false on any D-Bus error). On
   `WindowAdded(p)`: ignore `p` unless it is a known window; on an error
   or the same id, nothing; on a different id, store it and emit. It does
   not trust the sending application (queued signals of the temporary
   application arrive after the move). Every move ends with a
   `WindowAdded` from the final application, so the last one handled sees
   bamf's final state. Orders covered: move before the constructor's calls
   (right at once, later signals no-ops); move between them (the
   constructor's error gives the window number, the queued `WindowAdded`
   corrects it); move after `WindowCreated` (this card's case). No signal
   is handled for an unannounced window: `addWindow` and `WindowCreated`
   run in one slot, and the blocking calls do not dispatch signals.
3. **Order of the signals: `WindowCreated(new)`, then
   `FocusedWindowChanged(new)`, then `WindowDestroyed(old)`.** Destroyed
   first would set hud-service's focus to none (`removeWindow` on the
   emptied focused application) and clear an open query's results; and
   `ApplicationImpl::window` uses `QMap::operator[]`, which would insert a
   null entry into the old application. With Created first the focus goes
   straight to the new application.
4. **Focused from the bridge's own last `ActiveWindowChanged`** (a new
   member with that path), no extra synchronous `ActiveWindow()` call; a
   background window's move does not move the focus.
5. **Correction:** the bridge has no handling for a bamf owner change (no
   `QDBusServiceWatcher` in window-stack-bridge). Out of scope; on the
   target, "no crash, nothing worse than before".
6. **Destroy + create, no new `WindowApplicationChanged` signal:** the
   window's application id is fixed when hud-service builds its
   `WindowImpl` (collectors, usage keys), so a new signal would rebuild it
   anyway, in new code. Cost: one menu re-import per move.
7. **(B) and (C) are worse**, the bridge is the right layer (the only
   process here that talks to bamf); (B) would also miss the later move
   LibreOffice Start Center -> Writer.
8. **Unit tests** (tests/unit/window-stack-bridge/TestBamfWindowStack.cpp,
   the dbusmock helpers): a focused window moved from no desktop file to
   `appid-1` gives Created, Focused, Destroyed in that order and
   `GetWindowStack` returns `appid-1`; an unfocused window gives no
   Focused; the same application gives nothing; an unknown path gives
   nothing; a `DesktopFile` error keeps the id and emits nothing; after a
   move `ViewClosed` and `ActiveWindowChanged` carry the new id. Service
   side (tests/unit/service/TestApplicationList.cpp): Created(new),
   Focused(new), Destroyed(old) leaves the focused application the new one
   and no old id in `applications()`.
9. **Target measurements** (hud-service and window-stack-bridge restarted,
   no "(deleted)" mappings): 10 cold Writer starts and 3 Calc starts with
   libreoffice-writer / -calc in the stack each time; an open HUD query
   during the move still answers and `ExecuteCommand` works; the usage row
   under libreoffice-writer; no numeric application ids left in
   hud-service; Start Center -> a document; no bridge signals for a window
   bamf does not move (a terminal); bamfdaemon killed: the bridge stays up,
   what happens is recorded.

## Plan (before the Design Challenger)

1. Reproduction on Clean-2 + the published stack: window stack, the
   bridge's signals and bamf's signals for a cold Writer start (bamfwatch,
   dbus-monitor), and what the HUD shows (application name, icon) with the
   window-number id.
2. Existing fix: the -002 search covered later hud versions and forks
   (none); check bamf's own clients (libbamf `bamf_window_get_application`
   users, Unity's launcher) for how they follow a re-match.
3. Candidate approaches for the Design Challenger, e.g.: re-resolve the id
   when the matcher announces an application (`ViewOpened` of type
   application: ask its `Xids()`, and for each known window whose id is the
   window number, emit `WindowDestroyed(old)` + `WindowCreated(new)`); or
   subscribe to each application's `WindowAdded`; or resolve lazily in
   `GetWindowStack`/`ActiveWindowChanged`. Measure what hud-service does
   with a destroy/create pair for a live window (its menus are re-imported).
