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
