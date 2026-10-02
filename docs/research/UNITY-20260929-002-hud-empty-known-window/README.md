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

HYPOTHESIS A, kept until B is measured: on the first Writer start after a boot the window
is mapped, and bamf announces it, before LibreOffice attaches the menubar;
hud-service subscribes to a model with no items, indexes nothing, and the
`Changed` that follows never makes it re-index, so the HUD stays empty
for that window. On later starts the menubar is attached before bamf
announces the window. The earlier guess (properties missing at
`WindowCreated`) is dropped: LibreOffice sets them at frame creation.
