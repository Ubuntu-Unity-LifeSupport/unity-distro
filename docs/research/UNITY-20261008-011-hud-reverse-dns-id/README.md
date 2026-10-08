# UNITY-20261008-011: window-stack-bridge cuts reverse-DNS application ids at the first dot

Owner: agent B (target2). Found during UNITY-20260929-001 (its target
check). Done together with UNITY-20261008-014 (the bridge's missing tests
and small points): one hud revision `+unity5`, one Design Challenger
review, one build, one gate.

```yaml
task_id: UNITY-20261008-011 (+ UNITY-20261008-014)
package: hud (window-stack-bridge)
target_series: resolute
issue: local - found in UNITY-20260929-001
status: INVESTIGATING
source_version: 14.10+17.10.20170619-0ubuntu6+unity4 (published 2026-10-08)
observed: >
  window-stack-bridge gives every application whose desktop file has a
  reverse-DNS name the application id "org": on target2 29 applications
  (17 visible in the menu, Terminal, Disks, File Roller, Rhythmbox,
  Shotwell, Remmina, Mines, Help, ...). hud-service then treats them as
  one application: one usage history, one Application object, and no
  icon (it looks for org.desktop).
expected: >
  the application id is the desktop file id (org.gnome.Terminal), as for
  the applications without a dot in the name (libreoffice-writer).
```

## Reading the code (hud +unity4)

- `window-stack-bridge/BamfWindowStack.cpp`, `BamfWindow::resolveApplicationId`:
  the id is `QFileInfo(desktopFile).baseName()` for the desktop file bamf
  gives the window's application. `baseName()` is the file name up to the
  **first** dot, so `org.gnome.Terminal.desktop` gives `org`. This is the
  archive code (0ubuntu6, `c31857b`), unchanged by our revisions.
- hud-service uses the id in four places:
  - `ApplicationListImpl` keeps one `Application` per id, so windows of
    different applications under `org` share one object
    (`/com/canonical/hud/applications/org`);
  - `SqliteUsageTracker` keys the usage history by (id, entry), which
    orders the HUD results and the empty HUD's "most used" list;
  - `ApplicationImpl::desktopPath()` looks for `<id>.desktop` in
    `$XDG_DATA_DIRS/applications`, so `org.desktop`. It finds nothing, and
    `icon()` stays empty;
  - `HudServiceImpl` (legacy `StartQuery`) puts that icon into every
    suggestion, and `QueryImpl` puts it into the appstack model.
- The other client of `com.canonical.Unity.WindowStack` in our packages
  is indicator-keyboard (`lib/main.vala`, per-window input sources). It
  keys by window id and does not use `app_id` (`handle_focused_window_changed`,
  `handle_window_destroyed`).
- `DBusTypes::applicationPath()` escapes every character outside
  `[A-Za-z0-9]` (`.` becomes `_2e`), so a full desktop file id is a valid
  object path.

## Reproduction (2026-10-08, target2, logs/01, logs/02)

The setup: target2 restored to Clean-2, then upgraded to the live
publication `unity-resolute-20260929-001` (hud +unity4) with apt, then a
cold cycle (poweroff, then start).

- **The ids (logs/01, `ids.py` with the session's `XDG_DATA_DIRS`):**
  - 132 applications have a desktop file, 31 of them with a dot in the name;
  - 29 of them share the bridge id `org`, 17 of those visible;
  - `io` (snapd's session agent) and `python3` (`python3.14`) are cut too,
    but each stands alone.
- **One application object (logs/02):** with Terminal and Mines open, the
  stack lists both windows with `org`, and hud-service's `Applications`
  holds one `org` object (besides the desktop window, which has no bamf
  application). File Roller, Disks, Rhythmbox, Shotwell and Remmina's main
  window are `org` too.
- **Shared history (logs/02):**
  - Of these applications only Terminal has a menu of its own in the HUD;
    the others offer only the window actions, which every window has.
  - After "Всегда наверху" was run twice from the HUD in Terminal (the
    state ends where it started), the usage table holds
    `('org', 'Window actions||Всегда наверху', 2)`.
  - The empty HUD of Disks, File Roller and Mines then lists "Всегда
    наверху" first, although it was never used there.
  - Control: Writer, with its own id `libreoffice-writer`, keeps the
    default order ("Всегда наверху" fifth).
  - By the code, the same applies to every menu entry with the same path
    in two `org` applications. It was measured only for the window action.
- **Icon (logs/02):** the legacy `StartQuery` gives the icon
  `libreoffice-writer` in Writer's suggestions and an empty icon in
  Terminal's.
  - Not checked: whether Unity's HUD shows that empty icon. In
    UNITY-20260929-001 Unity took the HUD's icon from bamf. Opening the HUD
    with a single Alt tap through VirtualBox did not work this time.

## UNITY-20261008-014 (the same bridge)

The remarks of the UNITY-20260929-001 Verifier:

- no test that a `WindowAdded` from another bus name is ignored;
- no test where the application that sends `WindowAdded` differs from the
  window's `Parents()` answer. The bridge re-resolves from `Parents()`, so
  the sender should not matter;
- the bool returned by `m_connection.connect(... "WindowAdded" ...)` is not
  checked or logged (`BamfWindowStack.cpp:178`);
- `GetWindowStack` still uses `m_windows[path]`
  (`BamfWindowStack.cpp:229`), which inserts an empty entry for an unknown
  path.

## Existing-fix discovery (subagent, read-only, 2026-10-08)

Result: **NOT_FIXED**, issue search **NOT_FOUND**.

- **hud itself:** upstream `lp:hud` (trunk.15.10, last change 2020-03-16; 13
  merge proposals, none about window-stack-bridge ids), Ubuntu's hud
  0ubuntu1..0ubuntu6 (one 2017 snapshot, no debian/patches) and our mirror
  `Ubuntu-Unity-LifeSupport/hud` all have `baseName()`. Debian has no hud.
  UBports/Lomiri have no hud with a WindowStack bridge.
- **Launchpad:** nothing about reverse-DNS ids or HUD history shared
  between GNOME applications (hud and ubuntu/+source/hud, all statuses).
- **How the other consumers derive the id from a desktop file:**

  | consumer | rule | `org.gnome.Terminal.desktop` |
  |---|---|---|
  | bamf 0.5.6 `bamf-matcher.c:953` (its desktop-id table) | file name without the trailing `.desktop` | `org.gnome.Terminal` |
  | lomiri-app-launch `app-store-legacy.cpp:137` | `^(.*)\.desktop$` | `org.gnome.Terminal` |
  | unity7 `DesktopUtilities::GetDesktopID` | XDG desktop file ID, `.desktop` kept | `org.gnome.Terminal.desktop` |
  | libunity `unity-launcher.vala:230` | basename, `.desktop` kept | `org.gnome.Terminal.desktop` |

  None of them cuts at the first dot. KDE fixed the same `baseName()`
  mistake in Konsole by switching to `completeBaseName()`
  (commits.kde.org/konsole/a7c3bda7).
- **Subdirectories:** the XDG spec's desktop file ID turns
  `applications/kde4/foo.desktop` into `kde4-foo.desktop`. hud's
  `ApplicationImpl::desktopPath()` looks only in `applications/<id>.desktop`
  either way. target2 has no desktop file in a subdirectory of any
  `applications/` directory.

## Design (for the Design Challenger)

**Invariant:** the bridge's application id for a window is the desktop file
name without its `.desktop` suffix. It is the same id bamf uses for the
file, and `ApplicationImpl::desktopPath()` finds the file by it.

**UNITY-20261008-011, the id:**

1. **The code.** `BamfWindow::resolveApplicationId` takes
   `QFileInfo(desktopFile).fileName()` and removes a trailing `.desktop`
   (case-sensitive, as bamf does). A name without the suffix is kept whole.
   An empty desktop file still gives the window number. One helper,
   `applicationIdFromDesktopFile(const QString &)`, sits in the bridge,
   tested directly.
   - Why not `completeBaseName()`: it cuts at the last dot, so a name
     without `.desktop` (bamf can report a path it got from
     `_GTK_APPLICATION_ID` or a snap/flatpak id) would still lose its last
     component.
2. **Unchanged:**
   - ids without a dot: libreoffice-writer, gnome-mines and snaps' `firefox_firefox` stay byte for byte the same;
   - the window-number fallback and the UNITY-20260929-001 move;
   - `DBusTypes::applicationPath()`, which already escapes `.` as `_2e`;
   - the ignore list (`compiz`, `hud-gui`, `unknown`, empty).
3. **Not in scope:**
   - subdirectory desktop files keep the basename as today (`foo`, not `kde4-foo`); there are none on the reference target;
   - indicator-keyboard, the other WindowStack client, does not read the id.
4. **Existing usage rows.** The old rows under `org` (and `io`,
   `python3`) stay in users' tables and no longer match any application.
   They cannot be split back into applications, because the key lost that
   information. The applications concerned start with an empty history
   under their real id; for `org` that history was mixed anyway. No
   migration, as in UNITY-20260929-001 round 3.
5. **Effects to expect on target:**
   - Terminal: `org.gnome.Terminal`, Mines: `org.gnome.Mines`, and so on for the others;
   - hud-service has one Application per application;
   - the legacy StartQuery's icon field for Terminal becomes the desktop file's `Icon=`;
   - the empty HUD of Disks no longer shows Terminal's "Всегда наверху".

**UNITY-20261008-014, the same bridge:**

6. `GetWindowStack` uses `m_windows.value(path)`. An unknown path then
   inserts nothing; the loop skips null as it does now.
7. The `connect()` for `WindowAdded` is checked. On `false` the bridge
   logs a warning and goes on; the moves are then not followed, as before
   +unity4.
8. Tests:
   - `WindowAddedFromAnotherBusNameIsIgnored`: a second mock service, not
     `org.ayatana.bamf`, emits `WindowAdded` for a known window path whose
     Parents() would give another id. Expect no signals.
   - `WindowAddedFromAnotherApplicationUsesParents`: application B emits
     `WindowAdded`, while the window's `Parents()` says application C.
     Expect the move to C, not to B.

**Tests for -011:**

- bridge:
  - `ReverseDnsDesktopFileGivesFullId` (`/usr/share/applications/org.example.Foo.desktop` gives `org.example.Foo`, in WindowCreated and GetWindowStack);
  - `DesktopFileWithoutSuffixKeepsName` (`org.example.Foo` gives `org.example.Foo`);
  - a moved window to a reverse-DNS application (the move path uses the same helper);
  - the existing `appid-N` tests unchanged.
- service: `TestApplication.IconFromReverseDnsDesktopFile`: `XDG_DATA_DIRS`
  points at a temporary directory with
  `applications/org.example.Foo.desktop` (`Icon=foo-icon`), and
  `ApplicationImpl("org.example.Foo").icon()` is `foo-icon`. This pins the
  service side that the new id relies on.
- control: the new tests on the +unity4 bridge must fail exactly the -011
  bridge tests and the GetWindowStack/-014 tests that need the change. The
  service test passes on both, because the service code is unchanged.

**Target check (after APPROVE):** Clean-2 + the live publication, then
+unity5 from a file repository, then a cold cycle.

- before and after with the same steps as logs/02: the stack ids, hud-service `Applications`, the shared-history test, the legacy icon;
- Writer's id stays `libreoffice-writer` (the -001 move);
- 10 Writer starts;
- bridge SIGKILL restart.
