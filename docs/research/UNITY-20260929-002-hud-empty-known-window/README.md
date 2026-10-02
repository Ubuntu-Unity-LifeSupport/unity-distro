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

HYPOTHESIS, to measure: on the first start after a boot LibreOffice maps
its window before it sets `_GTK_UNIQUE_BUS_NAME` and
`_GTK_MENUBAR_OBJECT_PATH`; hud-service reads them at `WindowCreated`,
finds them empty, and never reads again, so the window has no menus until
it is closed. Later starts are fast enough that the properties are there
by the time bamf announces the window.
