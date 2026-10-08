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
status: VERIFIED (2026-10-08), publication next
source_version: 14.10+17.10.20170619-0ubuntu6+unity4 (published 2026-10-08)
observed: >
  window-stack-bridge gives every application whose desktop file has a
  reverse-DNS name the application id "org": on target2 29 applications
  (14 visible in the menu, Terminal, Disks, File Roller, Rhythmbox,
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
  - 29 of them share the bridge id `org`, 14 of those visible (15 are NoDisplay);
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

### Design review, round 1: REVISE (all points taken)

The Design Challenger (an independent subagent) confirmed the rule: file
name minus a trailing `.desktop`. It is bamf's own desktop-id rule
(`bamf-matcher.c:953-955`; bamf loads only names ending in `.desktop`,
`:998`). Ids whose only dot is the one in `.desktop` stay byte for byte the
same. Its points, as applied:

1. **The "Why not completeBaseName()" reason was wrong.** bamf's
   `DesktopFile()` ends in `.desktop` for the `_GTK_APPLICATION_ID` and
   snap/flatpak paths too (`:676`, `:1827`). A name without the suffix
   comes only from the `_BAMF_DESKTOP_FILE` window hint or
   `--desktop_file_hint` (`:33`, `:544`, `:2164`). The conclusion (keep such
   a name whole) stands, and an uppercase `.DESKTOP` is also kept whole.
2. **A fifth consumer of the id: `RegisterApplication`.**
   `HudServiceImpl.cpp:45-53` creates the Application for the id a libhud
   client sends, `g_application_get_application_id`, which is reverse-DNS
   (`libhud/manager.c:238`). Before the fix such a client's sources went to
   an Application (`org.gnome.Foo`) that none of its windows belonged to
   (they were under `org`). After the fix they meet. target2 has no libhud
   library installed (libhud2, libhud-client2, libhud-gtk1: not installed),
   so nothing there uses it.
   - The other consumers need no change:
     - `GetWindowProperties` ignores the id;
     - keywords come from the actions;
     - `UpdateApp` does nothing;
     - SQL binds values;
     - `applicationPath` escapes `.` and `_`, so paths stay valid and
       unique.
3. **Old usage rows:**
   - **They do not stay.** `store-usage-data` defaults to true, and rows
     older than 30 days are deleted at startup and daily
     (`SqliteUsageTracker.cpp:91-92`, `:105`).
   - **They are harmless meanwhile.** An application without history gets
     `usage() = 0` (`:135-137`) and the default order. After the change
     only a file literally named `org.desktop` (or a hint `org`) gives the
     id `org`; target2 has none (logs/01).
   - **The same holds for `io` and `python3`.** A future `io.desktop` or
     `python3.desktop` would inherit their rows for up to 30 days, which
     is negligible.
4. **Edge cases, decided and tested:**
   - **A subdirectory:** bamf walks subdirectories (`bamf-matcher.c:1205`),
     so `applications/kde4/foo.desktop` gives `foo`, as today.
     `desktopPath()` looks for `applications/foo.desktop` and finds no icon,
     as today. The rule and the lookup agree; the XDG id `kde4-foo` is out
     of scope.
   - **Several dots:** `org.gnome.Terminal.Preferences.desktop` gives
     `org.gnome.Terminal.Preferences`, and `python3.14.desktop` gives
     `python3.14`.
   - **No suffix:** a name is kept whole.
   - **A file named just `.desktop`:** today it gives `""`, and hud-service
     drops the window through its ignore list. +unity5 gives the window
     number instead, as for an empty desktop file, so the window keeps its
     window actions.
5. **Not in scope (pre-existing):** `desktopPath()` reads only
   `XDG_DATA_DIRS`, not `XDG_DATA_HOME`. User desktop files and files
   outside the XDG directories get the right id but no icon.
6. **`value()`:**
   - The null entry from `m_windows[path]` in `GetWindowStack` is never
     returned, because every reader uses `value()`, `take()` or
     overwrites it. So the change is behaviour-neutral, and no D-Bus test
     can tell +unity4 from +unity5. The test reads the protected maps
     through a test subclass.
   - `GetWindowProperties` and `GetWindowBusAddress` have the same insert
     on read (`m_windowsById[windowId]`). They get `value()` in the same
     change.
   - Logging a warning on a failed `connect()` and continuing is right.
7. **The two -014 tests are characterization tests.** They pass on
   +unity4 already: the connect filters by service name
   (`BamfWindowStack.cpp:178`), and the slot re-resolves from `Parents()`.
   The card now says so. Their mechanics:
   - **The second mock name** is registered before `dbus.startServices()`,
     in a fixture of its own.
   - **The negative test needs a sync point.** After the foreign emit, a
     real bamf `WindowAdded` for another moved window is waited for, and
     then the foreign one must have produced nothing.
   - **`Parents()` must already name another application**, so the test
     cannot pass vacuously.
8. **Control prediction by test name, the move test also checks
   `GetWindowStack`, an object path test, `XDG_DATA_DIRS` restored after
   the icon test:** see the revised design below.
9. **The target plan gets measured steps with expected values**, including
   the upgrade path with the old `org` row. Unity's HUD:
   `HudController::OnQuerySelected` sets the HUD icon from the selected
   result's `icon_name` with no fallback (unity `hud/HudController.cpp:510-514`).
   `OnQueriesFinished` falls back to bamf's icon only when all results
   have an empty icon (`:516-530`). So by the code, moving the selection
   onto a Terminal result blanks the HUD icon on +unity4.

## Design, revised after round 1

**Code (hud window-stack-bridge):**

- **The helper:** `applicationIdFromDesktopFile(path, windowId)`, a free
  function in `BamfWindowStack.cpp`, declared in the header for the tests.
  It takes `QFileInfo(path).fileName()`, removes a trailing `.desktop`
  (case-sensitive), and gives the window number for an empty path or an
  empty result. `resolveApplicationId` uses it, and so does the
  constructor's window-number fallback, which stays as it is.
- **`value()`:** `GetWindowStack` uses `m_windows.value(path)`;
  `GetWindowProperties` and `GetWindowBusAddress` use
  `m_windowsById.value(windowId)`.
- **The connect:** `connect(... "WindowAdded" ...)` is checked, and on
  failure the bridge logs
  `qWarning() << "Could not connect to bamf's WindowAdded; windows moved to another application keep their first id"`.

**Tests:**

| test | +unity4 (control) | +unity5 |
|---|---|---|
| `ApplicationIdFromDesktopFile` (helper: `org.example.Foo.desktop`, `org.gnome.Terminal.Preferences.desktop`, `python3.14.desktop`, `kde4/foo.desktop` → `foo`, `appid-1.desktop`, `org.example.Foo` (no suffix), `Foo.DESKTOP`, `.desktop` → window number, empty → window number) | does not build (no helper); the control replaces this test with the D-Bus ones below | pass |
| `ReverseDnsDesktopFileGivesFullId` (WindowCreated, GetWindowStack) | FAIL | pass |
| `MultiDotDesktopFileGivesFullId` (`python3.14.desktop`) | FAIL | pass |
| `SubdirectoryDesktopFileGivesBaseName` (`kde4/foo.desktop` → `foo`) | pass | pass |
| `DesktopFileWithoutSuffixKeepsName` (`org.example.Foo`) | FAIL (`org`) | pass |
| `DesktopFileNamedOnlySuffixGivesWindowNumber` (`/usr/share/applications/.desktop`) | FAIL (`""`) | pass |
| `WindowMovedToReverseDnsApplication` (Created/Focused/Destroyed and GetWindowStack after the move) | FAIL | pass |
| `UnknownPathsLeaveNoEntries` (subclass; the stack holds a path the bridge does not know; GetWindowStack, and GetWindowProperties and GetWindowBusAddress for an unknown id **over D-Bus** (InvalidArgs replies); map sizes equal to those right after construction) | FAIL | pass |
| `WindowAddedFromAnotherBusNameIsIgnored` (own fixture, second mock name; sync on a real bamf move) | pass (characterization) | pass |
| `WindowAddedFromAnotherApplicationUsesParents` | pass (characterization) | pass |
| service `TestApplication.ReverseDnsIdPathAndIcon` (`applicationPath("org.example.Foo")` = `/com/canonical/hud/applications/org_2eexample_2eFoo`, exported there; `XDG_DATA_DIRS` at a temporary `applications/org.example.Foo.desktop` with `Icon=foo-icon` gives `icon() == "foo-icon"`; `XDG_DATA_DIRS` restored) | pass | pass |

`createApplication` gets a desktop-file parameter (default
`appid-N.desktop`, as now). The control build is +unity4 plus the D-Bus
tests above. It must fail exactly `ReverseDnsDesktopFileGivesFullId`,
`MultiDotDesktopFileGivesFullId`, `DesktopFileWithoutSuffixKeepsName`,
`DesktopFileNamedOnlySuffixGivesWindowNumber`,
`WindowMovedToReverseDnsApplication` and `UnknownPathsLeaveNoEntries`.

**Target (after APPROVE; Clean-2 + the live publication, then measured
"before" on +unity4, then +unity5 from a file repository, cold cycle):**

| step | +unity4 (before) | +unity5 (expected) |
|---|---|---|
| stack ids: Terminal, Mines, Disks | `org` | `org.gnome.Terminal`, `org.gnome.Mines`, `org.gnome.DiskUtility` |
| hud-service `Applications` | one `org` | one per application, paths `..._2e...` |
| legacy StartQuery icon, Terminal "Создать окно" | `''` | `org.gnome.Terminal` (`Icon=` of its desktop file on target2) |
| legacy StartQuery icon, Writer "Сохранить" (control) | `libreoffice-writer` | `libreoffice-writer` |
| "Всегда наверху" twice in Terminal: usage row | `('org', …)` | `('org.gnome.Terminal', …)` |
| Disks' empty HUD after that | "Всегда наверху" first | default order; the `org` row from the before run is still in the table and has no effect |
| Terminal menu query "Создать окно" | 3 results from Файл | the same |
| Writer: 10 starts, the -001 move | `libreoffice-writer` | `libreoffice-writer` |
| bridge SIGKILL restart | ids as above | ids as above |
| Unity HUD icon with a Terminal result selected (optional screenshot, Down after opening) | blank by the code | Terminal's icon |

### Design review, round 2: REVISE (all points taken)

The Design Challenger accepted the two choices beyond round 1 and the
control table, with these changes:

1. **`UnknownPathsLeaveNoEntries` calls `GetWindowProperties` and
   `GetWindowBusAddress` over D-Bus**, through
   `ComCanonicalUnityWindowStackInterface` as the `OverDBus` test does.
   - For an unknown id both methods call `sendErrorReply` (`:267`,
     `:285`). Outside a D-Bus call the `QDBusContext` has no message, so a
     direct call would crash on both versions.
   - The test expects an `InvalidArgs` error reply and then reads the
     subclass's maps. The subclass is exported on the bus by the base
     constructor.
2. **The `GetWindowStack` part targets the stack loop** (`:229`), not the
   active-window lookup, which already uses `value()` (`:245`).
   - The mock's `WindowStackForMonitor` returns a path the bridge does not
     know. The test's `createMatcherMethods` puts the active path into the
     stack, so the test makes the active path an unknown one.
   - The map sizes are compared with the sizes right after construction.
3. **(a) accepted:** a file named only `.desktop` gives the window number.
   This is a deliberate behaviour change for an unlikely case, not part of
   the -011 fix. Today the empty id is ignored by hud-service, focus
   changes to that window are ignored too, and the HUD keeps showing the
   previous application's entries.
4. **(b) accepted:** `value()` in `GetWindowProperties` and
   `GetWindowBusAddress` is behaviour-neutral. The redundant `if (window)`
   in the loop stays. The test subclass needs no `Q_OBJECT`.
5. **Control:** the helper-only cases (`Foo.DESKTOP`, empty → window
   number) have no control counterpart. Empty is already covered on
   +unity4 by `HandlesWindowWhoseApplicationIsGone` and the no-desktop-file
   path.
6. **The warning for a failed `connect()` is untested.** A connect on the
   session bus cannot be made to fail through the mock, so it is checked by
   inspection only.
7. **The target plan stands as written.**

### Design review, round 3: APPROVE

The round-2 points are applied as asked; the Design Challenger checked
`20a007e..f3bdf2a` against the +unity4 code and tests. Remarks for the
implementation:

1. **The unknown active path:** `createMatcherMethods` also lists it in
   `WindowPaths`. Construction tries to add it, fails at `GetXid`, and
   does not insert it (as in `HandlesMissingWindow`), with a warning, so the
   constructor sits inside the file's "EXPECTED ERROR" lines. The map sizes
   are taken after construction. `GetWindowStack` may be called directly,
   because it never sends an error reply.
2. **Empty desktop file to window number:** on +unity4 this is covered by
   `HandlesWindowWhoseApplicationIsGone` and by the move tests using
   `createApplication(2, false)`. The only helper-only case is
   `Foo.DESKTOP`.
3. **The control:** exactly the six D-Bus tests listed above fail on
   +unity4. Its output goes into the card next to the table.

## Implementation (2026-10-08)

hud source `Ubuntu-Unity-LifeSupport/hud`, branch `b/UNITY-20261008-011`
(pushed), on the published +unity4 (`b0c2444`):

- `1fc54e1`: the bridge (`applicationIdFromDesktopFile`, `value()` in
  `GetWindowStack`/`GetWindowProperties`/`GetWindowBusAddress`, checked
  connect) and the tests of the revised design;
- `b1b8c7b`: +unity5;
- `db26b0d`: the tests' fix. A string literal converted to `bool` and
  called `createApplication(uint, bool)`, so the new id tests created
  `appid-0`.

The control is a local branch, `packages/hud-control`
`control/UNITY-20261008-011`: `b749260` (b0c2444 plus the D-Bus tests,
without the helper test), then `d5a32c2` (the same test fix).

**First builds** (12:3x-13:0xZ, before `db26b0d`, so not results):
- +unity5 failed 6 tests, and the control 7, all through that helper bug.
  On +unity5 `SubdirectoryDesktopFileGivesBaseName` failed, which no rule
  explains.
- The tests that did not use the overload behaved as predicted:
  `UnknownPathsLeaveNoEntries` failed on the control and passed on +unity5;
  both -014 tests passed on both; the service suite had 46 tests passing
  on both.

**Resume point** (stopped by C on 2026-10-08 ~13:15Z for the VBoxSVC
restart):
1. Rebuild both, `build/` from `db26b0d` and `build-control/` from
   `d5a32c2`, with `build_sbuild.py`.
2. Expected: +unity5 6/6 suites. The control fails exactly
   `ReverseDnsDesktopFileGivesFullId`, `MultiDotDesktopFileGivesFullId`,
   `DesktopFileWithoutSuffixKeepsName`,
   `DesktopFileNamedOnlySuffixGivesWindowNumber`,
   `WindowMovedToReverseDnsApplication` and `UnknownPathsLeaveNoEntries`.
3. After the restart, restore target2 to Clean-2 and confirm from inside
   the guest. It was powered off dirty at 13:06:31Z (live publication +
   hud +unity4 + the reproduction session).
4. Then the target plan above.

**Builds after the restart** (`build_sbuild.py`, chroot 20261008T083223Z; logs/04):

- +unity5 (`db26b0d`): 6 of 6 suites. window-stack-bridge has 33 tests, service 46.
- control (`d5a32c2`): the window-stack-bridge suite fails exactly the six predicted tests (`ReverseDnsDesktopFileGivesFullId`, `MultiDotDesktopFileGivesFullId`, `DesktopFileWithoutSuffixKeepsName`, `DesktopFileNamedOnlySuffixGivesWindowNumber`, `WindowMovedToReverseDnsApplication`, `UnknownPathsLeaveNoEntries`). 26 pass, among them both -014 tests and `SubdirectoryDesktopFileGivesBaseName`; the service suite passes, its new test included.

## Target check (target2, 2026-10-08, logs/03, logs/05)

**Setup:**
1. Clean-2 restored, checked from inside the guest (17:35Z): no `~/.dirty`, no work directories, none of our sources, no usage table, hud 0ubuntu6.
2. The live publication `unity-resolute-20260929-001` (hud +unity4) by the usual path, no drop-ins; cold cycle.
3. **Before** on +unity4 (`target011.sh`, logs/03).
4. hud +unity5 from a file repository, by `apt full-upgrade`. It also took `unity-settings-daemon` +unity12 from the live repository: A's UNITY-20261002-012 was published in between (the automount helper, not hud).
5. Cold cycle, then **after** with the same script (logs/05).
6. Both bridge and hud-service run from the installed binaries; no "(deleted)" mappings other than hud-service's `/tmp/#…` files.

| step | +unity4 (before) | +unity5 (after) |
|---|---|---|
| stack ids: Terminal, Mines, Disks | `org`, `org`, `org` | `org.gnome.Terminal`, `org.gnome.Mines`, `org.gnome.DiskUtility` |
| hud-service `Applications` | one `org` | one per application: `…/org_2egnome_2eTerminal`, `…/org_2egnome_2eMines`, `…/org_2egnome_2eDiskUtility` |
| legacy StartQuery icon, Terminal "Создать окно" | `''` | `org.gnome.Terminal` (the `Icon=` of its desktop file) |
| legacy StartQuery icon, Writer "Сохранить" (control) | `libreoffice-writer` | `libreoffice-writer` |
| Terminal "Создать окно" results | Создать окно, Создать вкладку, Закрыть окно (Файл) | the same |
| "Всегда наверху" twice in Terminal: usage row | `('org', …, 2)` | `('org.gnome.Terminal', …, 2)`; the before run's `('org', …, 2)` is still in the table |
| Disks' empty HUD after that | "Всегда наверху" first | default order ("Всегда наверху" fifth): the leftover `org` row has no effect |
| Writer, 10 starts (the UNITY-20260929-001 move) | (-001 logs/06) | `libreoffice-writer` 10 of 10. Six starts took the move (Created/Focused/Destroyed of the window number), four got the final id at once |
| window-stack-bridge SIGKILL | | restarted by systemd; the new process gives the same four ids |

**Not done:** the Unity HUD screenshot (optional in the design). By the code, the HUD icon follows the selected result's icon, which is now `org.gnome.Terminal`.

## Verification (independent Verifier, 2026-10-08): PASS

The Verifier did not write the fix. It re-measured the +unity5 state on
target2 itself. The +unity4 "before" state rests on logs/03 and the
control build.

- **Code** (`b0c2444..db26b0d`), against the revised design:
  - Every id goes through the rule: `resolveApplicationId` calls the helper, and the move takes its id from `resolveApplicationId`.
  - The constructor's fallback is unchanged.
  - Dot-free names keep their id: `appid-1` and `firefox_firefox` are pinned by the helper test.
  - `value()` is used at all three read sites; the only insert left is `addWindow`.
  - The connect is checked.
  - The `hud` .deb file lists of +unity4 and +unity5 are identical.
- **Tests:**
  - The control differs from the fix's tests only by the helper test.
  - It fails exactly the six tests, at their id and map-size assertions.
  - Both -014 tests are not vacuous: the foreign emit triggers no `Parents()` call, and the result (`appid-3`) is not the sender's id.
- **Provenance:** the manifest's tree hash equals `db26b0d^{tree}`, the .dsc source equals `git archive db26b0d`, and the hud .deb is `65ca0c56…` in the manifest, on disk and in target2's file repository.
- **target2:**
  - apt has +unity5 installed and as candidate, `dpkg -V hud` is clean, and no libhud is installed.
  - The running bridge and hud-service are the .deb's files, with no "(deleted)" mappings.
  - No unit drop-ins or overrides (only systemd's generic graphical-session-pre one).
- **Its own check with File Roller** (an application the owner did not test):
  - It gets the id `org.gnome.FileRoller`, its own Application, and the legacy icon `org.gnome.FileRoller`.
  - "Развернуть на весь экран" and then "Восстановить прежний размер" from the HUD leave the window state as before. The usage rows go under `org.gnome.FileRoller` only.
  - File Roller's empty HUD then starts with "Развернуть на весь экран". Mines and Disks keep the default order, and Terminal keeps its own history.
- **The old `org` row:** it has no effect. No `org.desktop`, `io.desktop` or `python3.desktop` exists, and there are no desktop files in subdirectories.
- **The connect:** the bridge journal of this boot has no "Could not connect" warning.

Remarks:

1. The card said "17 visible" `org` applications. logs/01 has 29, 15 of them NoDisplay, so 14 are visible. Corrected above.
2. The evidence records of both tasks had template values in some fields (-014: root cause, invariant, approach, layer, reproduction record; both: verification, version-check and gate paths). They were filled in before the gate.
3. The constructor's window-number fallback still uses `QString::number(m_windowId)` directly, not the helper as the design said. The behaviour is the same.
4. `ReverseDnsIdPathAndIcon` does not restore `XDG_DATA_DIRS` when an ASSERT fails, and restores an unset variable as empty. This is harmless in the test binary.
5. `ids.py`'s docstring named a column the script does not print. Corrected.
6. **Left on target2:** two usage rows under `org.gnome.FileRoller`. After maximize and restore, File Roller's window was 32 px off its first geometry; its state flags were back to normal.
7. **An unexplained journal line.** The bridge instance that ran before the SIGKILL (pid 2126) logged `QDBusConnection: name 'org.ayatana.bamf' had owner '' but we thought it was ':1.34'` once. It is not seen in the current instance and was not investigated.
8. **Not checked:** the Unity HUD icon on screen; the failed-connect log path (by inspection only, as designed); the +unity4 state re-measured by the Verifier.

## Known gaps

| gap | where it is covered |
|---|---|
| Desktop files in subdirectories keep the base name (`kde4/foo` → `foo`), not the XDG desktop file id `kde4-foo`; hud-service then finds no icon for them. | none on the reference target (no such files); out of scope by design |
| User desktop files (`~/.local/share/applications`, `XDG_DATA_HOME`) get the right id but no icon: `desktopPath()` reads only `XDG_DATA_DIRS`. | pre-existing; follow-up UNITY-20261008-017 |
| The failed-connect warning is untested (a session-bus connect cannot be made to fail through the mock). | by inspection only |
| The Unity HUD's on-screen icon after the fix is not seen. | by the code it follows the selected result's icon, which the legacy StartQuery now gives as `org.gnome.Terminal` (logs/05) |
| Old usage rows under the cut ids (`org`, `io`, `python3`) stay until hud's 30-day expiry. | harmless (logs/05: no effect in Disks' empty HUD) |
| The `org.ayatana.bamf` owner warning of the first bridge instance (remark 7) is not explained. | seen once, not again after the restart; follow-up UNITY-20261008-018 |
