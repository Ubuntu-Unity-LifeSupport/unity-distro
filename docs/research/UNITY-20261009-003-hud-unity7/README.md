# hud +unity7: UNITY-20261009-003, -004 and -005

Owner: agent B (target2). One hud revision, `14.10+17.10.20170619-0ubuntu6+unity7`, on the published +unity6
(`1369d9e`, UNITY-20261008-025). One Design Challenger review, one build, one gate.

```yaml
tasks:
  UNITY-20261009-003: hud-service legacy ExecuteQuery crash paths - a non-integer item key, and no focused window
  UNITY-20261009-004: the Unity 7 HUD command "Создать окно (Файл)" for gnome-terminal opens no window
  UNITY-20261009-005: a relative XDG_DATA_HOME is not ignored by the desktop-file lookup
corrections to the board titles (in the evidence):
  -004: the use is recorded under org.gnome.Terminal on our stack ('org' was the Ubuntu base only); the bug is the
        missing window
  -005: the code is hud-service ApplicationImpl::desktopPath, not window-stack-bridge
package: hud
target_series: resolute
source_version: 14.10+17.10.20170619-0ubuntu6+unity6 (published 2026-10-09)
status: INVESTIGATING
```

## Reading the code (hud +unity6, `1369d9e`)

### -004: libqtgmenu never sends a menu item's target

A GMenu item names an action and may carry a target, the parameter for the action
(`G_MENU_ATTRIBUTE_TARGET`). GTK activates an item with `g_action_group_activate_action(group, name, target)`. The
reference is `gtk_menu_tracker_item_activated` in GTK's `gtkmenutrackeritem.c`, and qmenumodel does the same.

libqtgmenu loses the target in two places:

- **`QtGMenuModel` (`libqtgmenu/internal/QtGMenuModel.cpp:395-440`)** builds a `QAction` from each item. It reads
  the label, the action name, the icon and `accel`, but never `G_MENU_ATTRIBUTE_TARGET`. That attribute is read
  nowhere in libqtgmenu.
- **`QtGActionGroup::TriggerAction` (`libqtgmenu/internal/QtGActionGroup.cpp:75-103`)** gets only the action name
  and `checked`. It asks the action group for the parameter type:
  - no parameter: it activates with `nullptr`;
  - a string parameter: it activates with **the action's own name** as the value;
  - any other parameter type: **it does nothing**. The source says `///! need to evaluate and send parameter
    value`.

The trigger path: `QAction::triggered` → `QtGMenuModel::ActionTriggered(bool)` → `ActionTriggered(QString name,
bool checked)` (through the child models, :385) → `QtGMenuImporterPrivate` (:129) → every `QtGActionGroup::
TriggerAction`; each group keeps only the actions of its own prefix (`app.`, `win.`, ...).

`ItemStore::executeItem` marks the use (`m_usageTracker->markUsage`) whether or not the action ran. That is why the
usage table records the Terminal command although nothing happened.

### -003: two crash paths in `QueryImpl::ExecuteCommand` (`service/QueryImpl.cpp:122-135`)

```cpp
if (!item.variant().canConvert<qlonglong>()) {
	qWarning() << "Failed to execute command - invalid item key" << item.variant();
	sendErrorReply(QDBusError::InvalidArgs, "Failed to execute command - invalid item key");
	return;
}
qulonglong commandId(item.variant().toULongLong());
m_windowToken->execute(commandId);
```

- **The non-integer key.** The legacy path is the one Unity 7 uses. There `HudServiceImpl::ExecuteQuery` calls
  `query->ExecuteCommand(itemKey, timestamp)` directly, not over D-Bus on the query object. So `QueryImpl` has no
  D-Bus context, and `QDBusContext::sendErrorReply` dereferences a missing message. `ExecuteParameterized` (:156) has
  the same pattern.
- **A string key.** `QVariant::canConvert<qlonglong>()` is true for a string in Qt 5, and `toULongLong()` gives 0 for
  "not-a-number". So a string key runs item 0, silently.
- **No focused window.** `m_windowToken` is set only in `refresh()` when `m_applicationList->focusedWindow()` is not
  null (:200-205). `ExecuteCommand` (:134) and `ExecuteParameterized` (:166) dereference it without a check; the
  toolbar methods (:92, :100) do check.
  - `focusedWindow()` is null when the focused application is reset: window-stack-bridge leaves the bus
    (`ApplicationListImpl::serviceUnregistered`), or the focused application's last window closes.
  - It is also null when `FocusedWindowChanged` names an application or window hud-service does not know yet:
    `m_applications[applicationId]` and `application->window(id)` use `operator[]`.

### -005: the desktop-file lookup and a relative `XDG_DATA_HOME`

+unity6 (UNITY-20261008-017) made `ApplicationImpl::desktopPath` use
`QStandardPaths::locate(ApplicationsLocation, "<id>.desktop")`. Qt 5.15 drops relative `XDG_DATA_DIRS` entries, but
takes `XDG_DATA_HOME` as it is. The XDG Base Directory spec says a relative value is invalid and must be ignored,
which means falling back to `$HOME/.local/share`.

## Reproduction (2026-10-12, target2, logs/01-04)

The setup (logs/00):

- Clean-2 restored and confirmed from inside;
- the live archive the usual way, `apt full-upgrade` (hud +unity6, unity +unity13, gnome-terminal 3.58.0);
- xdotool, x11-utils, gdb, g++ and qtbase5-dev for the probes;
- a cold cycle.

The running hud-service is the published +unity6 (sha256 `3471e07f…`). The legacy client `hudexec.py` makes the
calls Unity 7 makes (StartQuery, ExecuteQuery with the suggestion's key, CloseQuery). `repro.sh`, `nowin2.sh` and
`bt003.sh` hold the steps.

- **UNITY-20261009-004, reproduced (logs/01).**
  - gnome-terminal's item "Создать _окно" is `win.new-terminal` with the target `('window', 'current')`; the
    action's parameter type is `(ss)`.
  - The HUD finds the item (key 7), and ExecuteQuery returns. **No `org.gtk.Actions` call reaches the terminal**:
    dbus-monitor sees 0 `Activate`, and the terminal still has 1 window.
  - Control: `org.gtk.Actions.Activate` of `new-terminal` with that target, sent by hand, opens a second window.
- **UNITY-20261009-003, the non-integer key, reproduced (logs/02).**
  - A string key returns normally, with no crash. It is taken as item 0, per the reading above.
  - A D-Bus structure key logs "Failed to execute command - invalid item key QVariant(QDBusArgument, )", then
    **hud-service dies with SIGSEGV**: the client gets "NoReply", apport writes a crash report with Signal 11, and
    no hud-service is left until the next call activates it again.
  - Under gdb: `#0 QDBusContext::message() const`, `#1 QDBusContext::setDelayedReply(bool)`, `#2
    QDBusContext::sendErrorReply(...)`, called from hud-service.
- **UNITY-20261009-003, no focused window: NOT reproduced live (logs/03).** In four tries hud-service still knew a
  focused window, and nothing crashed:
  - every application window closed and the desktop focused;
  - window-stack-bridge killed with SIGKILL, and the query sent at once;
  - the only application window closed, and the query sent at once;
  - hud-service stopped, and the query that starts it sent at once.

  The defect stands on the code reading. A unit test shows it, with a mocked application list that has no focused
  window.
- **UNITY-20261009-005, reproduced with a Qt probe (logs/04).**
  - `qpaths.cpp` on target2 with Qt 5.15.18, run in a directory holding `rel/applications/x.desktop`, with
    `XDG_DATA_HOME=rel`: Qt lists `rel/applications` first and `locate()` returns `"rel/applications/x.desktop"`, a
    path relative to the working directory.
  - With the absolute value: `"/tmp/…/rel/applications/x.desktop"`.
  - The Unity session does not set `XDG_DATA_HOME` (UNITY-20261008-025 Verifier), so this does not happen on our
    stack today.

## Existing-fix discovery (subagent, read-only, 2026-10-12)

| bug | result |
|---|---|
| -004 TriggerAction ignores the target | NOT_FOUND |
| -003 ExecuteCommand crash paths | NOT_FOUND |
| -005 relative `XDG_DATA_HOME` | NOT_FOUND (only our own +unity6 touches the lookup) |

- **Ubuntu:** hud `14.10+17.10.20170619-0ubuntu6` is the newest in every series, stonking (26.10) included. The
  check was the Launchpad `getPublishedSources`. 0ubuntu2..6 are build fixes only.
- **Debian:** hud is not packaged.
- **lp:hud:** `trunk.15.10` last changed 2020-03-16; there is no newer upstream.
- **Forks:** none found on GitLab `ubports` or gitlab.com/ubuntu-unity. qmenumodel (UBports) passes the target, as
  GTK does.
- **Related reports:**
  - [LP #1288025](https://bugs.launchpad.net/hud/+bug/1288025) "HUD entries don't get activated with gmenumodel"
    is the original activation fix, which left the target unfinished.
  - [LP #1415840](https://bugs.launchpad.net/ubuntu/+source/hud/+bug/1415840) (Chromium menu items do nothing from
    the HUD) has the same symptom; its cause was never confirmed.
- **Gaps:** the lp:hud revision log itself could not be listed, and PPAs were not checked.

## Design (for the Design Challenger)

One hud revision, +unity7, on `1369d9e`. Tests first, so that a control build of the tests on +unity6 shows them
failing.

### -004: pass the item's target, as GTK does

1. **`QtGMenuModel`:** when it builds the `QAction`, read `G_MENU_ATTRIBUTE_TARGET`
   (`g_menu_model_get_item_attribute_value(model, index, G_MENU_ATTRIBUTE_TARGET, NULL)`). Keep it as a new
   property `c_property_actionTarget`, holding the typed text of `g_variant_print(target, TRUE)`; empty when the
   item has none.
2. **The trigger signal carries it:** `ActionTriggered(QString name, bool checked, QString target)`, along the same
   chain (`QtGMenuModel` and its children, `QtGMenuImporterPrivate`, `QtGActionGroup::TriggerAction`).
3. **The choice of parameter moves into a static function** that can be tested without D-Bus, for example
   `QtGActionGroup::ActivationParameter(const GVariantType *type, const QString &target, const QByteArray &name,
   bool *activate)`:
   - **a target, and the action takes a parameter of the target's type** (`g_variant_is_of_type`): activate with
     the target. This is the GTK case and fixes -004.
   - **a target, but the action takes no parameter:** activate without one. Sending a parameter to an action that
     takes none makes the application refuse the call.
   - **a target of the wrong type:** do not activate, and log it.
   - **no target:** the current behaviour, unchanged: no parameter → `nullptr`; a string parameter → the action's
     name, the existing fallback, kept for compatibility; other types → nothing. Applications that rely on the
     fallback keep working.
4. **`TriggerAction`** parses the text back with `g_variant_parse` and activates with the chosen parameter.

**Tests (TestQtGMenu has only DISABLED_ tests, so a new test file in `tests/unit/qtgmenu`):**

- `ActivationParameter` for every row above;
- an integration test: a `GSimpleActionGroup` with a `(ss)` action, exported on the test session bus;
  `QtGActionGroup` connected to it; `TriggerAction("win.x", false, "('window', 'current')")`; the action's
  `activate` signal must receive that value. If the test bus setup of the qtgmenu suite is not usable, this part
  moves to the target check.

### -003: no crash on a bad key or without a window

In `QueryImpl::ExecuteCommand` and `ExecuteParameterized`:

- **Read the key with `toULongLong(&ok)`** and reject when `!canConvert<qlonglong>()` or `!ok`. A string such as
  "not-a-number" is rejected; a numeric string still works.
- **Reply with an error only when the call came over D-Bus to the query** (`calledFromDBus()`). Otherwise
  `qWarning` and return. The legacy caller, `HudServiceImpl::ExecuteQuery`, then just returns, as it does today for
  an unknown key.
- **`m_windowToken` null:** `qWarning` "no focused window", the same error reply rule, return.

**Tests in TestQuery:**

- `ExecuteCommandWithStructureKeyOutsideDBus`: no crash, nothing executed;
- `ExecuteCommandWithNonNumericStringKey`: nothing executed;
- `ExecuteCommandWithoutFocusedWindow`: the application list mock returns a null window, so no crash and nothing
  executed;
- the same for `ExecuteParameterized`.

### -005: ignore a relative `XDG_DATA_HOME`

In `ApplicationImpl::desktopPath`:

- **If `XDG_DATA_HOME` is set and not absolute,** search `$HOME/.local/share/applications` first (the spec's
  default), then `QStandardPaths::standardLocations(ApplicationsLocation)` without its first entry. That entry is
  Qt's location built from the relative value.
- **Skip any relative entry,** and take the first directory that holds `<id>.desktop` as a file.
- **Otherwise,** keep `QStandardPaths::locate` as it is.

**Test in TestApplication:** `RelativeDataHomeIgnored`, with its own `HOME`, `XDG_DATA_HOME=rel`, a working
directory that holds `rel/applications/<id>.desktop`, and `$HOME/.local/share/applications/<id>.desktop`. The
desktop path must be the `$HOME` one, absolute.

### What is not changed

- `HudServiceImpl::ExecuteQuery` still gives the legacy caller no error reply.
- The usage table records a use even when the action did not run. That is old behaviour, and outside these tasks.
- The two `operator[]` lookups in `ApplicationListImpl::FocusedWindowChanged` and `ApplicationImpl::window`.
  Candidate (ID from C) if the Design Challenger thinks they belong here.

### Design review, round 1: REVISE (all points taken)

The direction holds for the three tasks. Ten changes before code:

1. **The -004 end-to-end test goes through the legacy API, in `tests/integration/TestHud.cpp`.**
   - `QtGActionGroup` marks every action with a parameter type as parameterized, target or not
     (`QtGActionGroup.cpp:131`, `:150-151`; `QtGMenuModel.cpp:184-193`). `HudClient::executeCommand` sends such rows
     to `ExecuteParameterized` and never to `ExecuteCommand` (`libhud-client/HudClient.cpp:330-331`). So a test
     copied from `TestHud.ExecuteGMenuAction` would fail with and without the fix.
   - Unity 7 is not affected: the legacy `Suggestion` has no such flag (`HudServiceImpl.cpp:158-161`).
   - The test drives `com.canonical.hud` `StartQuery`/`ExecuteQuery` as Unity 7 does. It uses a new menu fixture
     `tests/menus/test-menu-input-model-target.c` with:
     - an `(ss)` item with a target;
     - an `s` radio item with a target;
     - a stateful boolean without one;
     - a parameterless action with a target, which must not activate.
   - Not changed: new-API clients keep treating targeted items as parameterized (a candidate).
2. **The decision table, compared with GTK** (`gtk_menu_tracker_item_action_added`:
   `can_activate = (!target && !ptype) || (target && ptype && g_variant_is_of_type(target, ptype))`):
   - **a target, but the action takes no parameter:** do not activate, and log it.
   - **an unknown action:** `g_action_group_query_action` first, so it is told apart from "no parameter".
   - **the string fallback:** "no target, string parameter → the action's name" is kept, and labelled as hud's own
     compatibility rule.
   - **radio items:** the card states that a radio item with a target changes on purpose: before, its value was
     the action's name; now it is its target.
3. **Check and radio items are not broken:** `checked` is unused (`QtGActionGroup.cpp:75-103`), no QAction is
   checkable (`QtGMenuModel.cpp:394-469`), and a boolean toggle still gets `activate(NULL)`, so GLib toggles it.
   Nothing starts calling `change_action_state`.
4. **The target as text is acceptable.**
   - Parse with `g_variant_parse(NULL, …)` and check the type with `g_variant_is_of_type` only afterwards.
   - Unref both the attribute value and the parsed variant; `ActivationParameter` documents who owns the result.
   - A parse failure counts as the "wrong type" case.
5. **The signal change.**
   - Every site is in libqtgmenu: `QtGMenuModel.h:67,75`, `QtGActionGroup.h:53`, the emit at `QtGMenuModel.cpp:169`,
     and the string connections at `QtGMenuModel.cpp:385-386` and `QtGMenuImporterPrivate.cpp:129-130`.
   - Switch these to function-pointer connections, with `qOverload` (the slot `ActionTriggered(bool)` overloads the
     signal), so a mismatch fails at compile time.
   - The dbusmenu path is untouched; toolbar items get the fix through `executeItem`.
6. **`calledFromDBus()` is the right guard.** In Qt 5.15 the context is stored only on the object that received the
   call: `HudServiceImpl` for Unity's `ExecuteQuery`, `QueryImpl` for a call on the query path. Add a test for the
   second branch: a bad key over D-Bus on the query path gets `InvalidArgs`.
7. **An unknown key changes the store.**
   - `ItemStore::execute`, `executeParameterized` and `executeToolbar` use `m_items[...]` (`ItemStore.cpp:299`,
     `:307`, `:339`), which inserts a null item.
   - The next new-API `SHOW_SUGGESTIONS` search dereferences it (`:185-186`), and `toolbarItems()` lists a bogus
     name (`:361-363`).
   - Use `value()`, and add a TestItemStore test (an unknown id, then an empty `SHOW_SUGGESTIONS` search).
   - A negative `'x'` key wraps to a huge id; it is now harmless.
8. **No other unchecked `m_windowToken` use.** The string-key test needs a focused window and
   `EXPECT_CALL(*windowToken, execute(_)).Times(0)`, otherwise it passes on +unity6. On +unity6 the structure-key and
   no-window tests end in SIGSEGV, so the control runs each new test with its own `--gtest_filter`.
9. **-005, tightened.**
   - **When it applies:** `XDG_DATA_HOME` non-empty and not starting with `/` (decoded with `QFile::decodeName`).
     Not `QDir::isAbsolutePath`, which calls `:/x` absolute. A `~/x` value is relative.
   - **The lookup:** the default from `QDir::homePath()`, then `standardLocations(...).mid(1)` with a comment
     (Qt prepends exactly one writable entry), checked with `QFileInfo::isFile`.
   - **The test:** a scoped guard restores the working directory.
   - The three +unity6 tests stay valid.
10. **The control.**
    - `ActivationParameter` does not exist on +unity6, so its unit test stays outside the control, in its own file
      under `tests/unit/qtgmenu` without the disabled `TestQtGMenu` fixture.
    - The control runs the TestHud target test, the TestQuery and TestItemStore tests and `RelativeDataHomeIgnored`.
    - Why the qtgmenu tests are disabled is not recorded; no D-Bus test goes into that fixture.
    - Scope is otherwise right: the icon and submenu paths lose no target.

## Reach of -004 (2026-10-12, target2, logs/05)

The survey covers the application set of UNITY-20261008-001 (43 GTK4 and 10 GTK3 applications) plus
gnome-terminal and libunity-gtk4-menu0, 56 packages installed for it.

- **Setup:** our packaged stack as a user has it: gtk-nocsd 4.8-1+unity3, libunity-gtk4-menu0 0.9 installed
  explicitly, the session's own `LD_PRELOAD=libunity-gtk4-menu.so.0:libgtk-nocsd.so.0`, after a cold cycle.
- **Method** (`survey.sh`, `survey.py`): each application is started alone. Every GMenu it exports is walked
  (`org.gtk.Menus` on `_GTK_MENUBAR_OBJECT_PATH` and `_GTK_APP_MENU_OBJECT_PATH`). For every item, the survey records
  the target's GLib type and the action's parameter and state type (`org.gtk.Actions.Describe` on the application or
  window group). That is the input of hud's libqtgmenu.
- **`analyze.py`** applies +unity6's `TriggerAction` and the revised table to every item.

55 applications were surveyed; 38 export menu items, 306 items with an action in all. One error: Showtime's menubar
timed out, as in UNITY-20261008-001.

| target type | parameter type | items | +unity6 | revised design |
|---|---|---|---|---|
| none | none | 243 | `activate(NULL)` | `activate(NULL)` |
| `s` | `s` | 37 | **activates with the action's name** | activate with the target |
| `(uu)` | `(uu)` | 4 | **nothing** | activate with the target |
| `b` | `b` | 3 | **nothing** | activate with the target |
| `x` | `x` | 3 | **nothing** | activate with the target |
| `(ss)` | `(ss)` | 2 | **nothing** | activate with the target |
| (no group for the prefix, or no such action) | - | 14 | nothing: no group matches the prefix | no activation (unknown) |

- **In every targeted item, the target's type equals the action's parameter type.** No row "target but no parameter"
  or "wrong type" occurs. So the fix needs no per-type code: it passes the target and checks the type.
- **49 items in 14 applications are run wrongly or not at all by the HUD today.**
  - The 12 non-string items are never activated:
    - gnome-terminal: New Tab and New Window (`(ss)`), Reset and Reset and Clear (`b`), the four sizes (`(uu)`);
    - celluloid: the video, audio and subtitle tracks (`x`);
    - Text Editor: Discard Changes (`b`).
  - The 37 string items get the action's name instead of their target:
    - radio choices in Calculator (number format), Maps (measurement system), Weather (temperature unit), File Roller
      (list mode), Swell Foop (colours, theme), Shortwave (sorting) and Amberol (ReplayGain);
    - Terminal's copy and close variants;
    - Celluloid's "load track" items.

    The application gets a value it does not expect and ignores it or sets nothing. All of these are radio items or
    selectors, so the result of the HUD command is wrong rather than harmful.
- **Our own libunity-gtk4-menu is affected too.** Some affected items are its own `win.unity-gtk4-menu-*` actions:
  Amberol ReplayGain, Shortwave sorting, Text Editor Discard Changes. The fix makes them work through the HUD.
- **The 14 "unknown" items stay as they are.** They fall in two groups:
  - actions whose group is not exported where the HUD looks: `ui.`, `game-view.`, `restore.`, Epiphany's;
  - actions the window does not have: Terminal's save-contents, export, print, set-title.

  +unity6 finds no group and does nothing; the revised design logs them and does nothing. They match the
  "MISSING" items of UNITY-20261008-001.

## Design, revised after round 1

The parameter types the fix must handle are measured across applications in "Reach of -004" below.

### -004

- **The target travels:** `QtGMenuModel::CreateAction` reads `G_MENU_ATTRIBUTE_TARGET` and stores
  `g_variant_print(target, TRUE)` as the property `actionTarget`; the attribute is unreffed.
- **The signal carries it:** `ActionTriggered(QString name, bool checked, QString target)`. The three connections
  use function pointers (`qOverload` where needed).
- **`QtGActionGroup::ActivationParameter`** is static and pure. It takes `known` (from `g_action_group_query_action`),
  the parameter type, the target text and the action name, and returns `{activate, GVariant *parameter}`, where the
  parameter is owned by the caller:

  | known | target | parameter type | result |
  |---|---|---|---|
  | no | any | - | no activation, log "unknown action" |
  | yes | none | none | activate with `NULL` (toggles and plain actions as now) |
  | yes | none | `s` | activate with the action name (hud's compatibility rule, kept) |
  | yes | none | other | no activation (as now) |
  | yes | parses, and is of the type | any | activate with the target (GTK) |
  | yes | present | none | no activation, log (GTK: insensitive) |
  | yes | wrong type or does not parse | any | no activation, log |

- **`TriggerAction`** calls it, activates, and unrefs the parameter.

### -003

- **`QueryImpl::ExecuteCommand` and `ExecuteParameterized`:**
  - reject when `!canConvert<qlonglong>()` or `toULongLong(&ok)` fails;
  - when `m_windowToken` is null, return;
  - in both cases `qWarning`, and `sendErrorReply` only when `calledFromDBus()`.
- **`ItemStore::execute`, `executeParameterized`, `executeToolbar`:** `m_items.value(...)`, so an unknown id
  inserts nothing.

### -005

- **`ApplicationImpl::desktopPath`:** when `XDG_DATA_HOME` is non-empty and its decoded value does not start with
  `/`, search `QDir::homePath() + "/.local/share/applications"` first, then
  `QStandardPaths::standardLocations(ApplicationsLocation).mid(1)`. The comment says why `mid(1)`. Take the first
  `QFileInfo(dir + "/" + name).isFile()`. Otherwise use `QStandardPaths::locate` as in +unity6.

### Tests

- **Control (the tests on +unity6):**
  - `TestHud`: the legacy target test with `test-menu-input-model-target.c`. The `(ss)` item runs with its target,
    the `s` radio item gets its target, the boolean toggles, the parameterless action with a target does not run.
  - `TestQuery`:
    - a structure key outside D-Bus;
    - a non-numeric string key with a focused window (`execute` never called);
    - no focused window;
    - a bad key over D-Bus on the query path (`InvalidArgs`, which already passes on +unity6);
    - `ExecuteParameterized` with the same keys.
  - `TestItemStore`: an unknown id, then an empty `SHOW_SUGGESTIONS` search.
  - `TestApplication`: `RelativeDataHomeIgnored`.
  - Each runs with its own `--gtest_filter` in the control log.
- **Outside the control:** `tests/unit/qtgmenu/TestActivationParameter.cpp`, one test per table row.

### Not changed (candidates, IDs from C)

- New-API clients treat targeted items as parameterized.
- The usage table records a use even when nothing ran.
- The `operator[]` lookups in `ApplicationListImpl::FocusedWindowChanged` and `ApplicationImpl::window`. They give
  null windows, which the -003 guard now handles.
