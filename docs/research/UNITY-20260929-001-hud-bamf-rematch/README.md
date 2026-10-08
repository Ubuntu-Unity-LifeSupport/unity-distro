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
