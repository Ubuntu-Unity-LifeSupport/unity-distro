# hud +unity6: UNITY-20261008-025, -017 and -018

Owner: agent B (target2). One hud revision, `14.10+17.10.20170619-0ubuntu6+unity6`, on the published +unity5
(`db26b0d`). It carries three tasks found during UNITY-20261008-011 and -013, with one Design Challenger review,
one build and one gate.

```yaml
tasks:
  UNITY-20261008-025: hud-service keeps a legacy StartQuery whose sender never calls CloseQuery for the life of
    the service, together with its query and Columbus Matcher (found by the UNITY-20261008-013 Verifier)
  UNITY-20261008-017: an application whose desktop file is only in ~/.local/share/applications gets the right id
    but no desktop path and no icon (UNITY-20261008-011, known gap 2)
  UNITY-20261008-018: window-stack-bridge logged once "QDBusConnection: name 'org.ayatana.bamf' had owner '' but
    we thought it was ':1.34'" at its first start (UNITY-20261008-011, Verifier remark 7); first reproduce it
package: hud
target_series: resolute
source_version: 14.10+17.10.20170619-0ubuntu6+unity5 (published 2026-10-08)
status: INVESTIGATING
```

## Reading the code (hud +unity5, `db26b0d`)

**UNITY-20261008-025.**
- **The legacy interface** (`service/HudServiceImpl.cpp`, used by Unity 7's HUD) keeps one query per D-Bus sender
  in `m_legacyQueries` (a `QMap<QString, QPair<Query::Ptr, QSharedPointer<QTimer>>>`). The query is closed only by
  `ExecuteQuery`, or by `CloseQuery` followed by a 2 s timer (`legacyTimeout`). The comment in `CloseQuery` says
  legacy queries are kept on purpose, because Unity 7 would otherwise build and destroy one per key press.
- **The sender watcher.** Every query, legacy ones included, is a `QueryImpl` that watches its sender
  (`QDBusServiceWatcher`, `WatchForUnregistration`, `QueryImpl.cpp:39-44`). When the sender leaves the bus,
  `QueryImpl::serviceUnregistered()` calls `CloseQuery()`, then `HudServiceImpl::closeQuery(path)`.
- **The defect.** `HudServiceImpl::closeQuery(path)` only does `m_queries.take(path)`. For a legacy query the
  `m_legacyQueries` entry still holds the `Query::Ptr`, so the query, its result models and its Matcher (three
  libcolumbus Tries) live until hud-service exits. A sender that leaves without `CloseQuery` (a one-off `gdbus
  call`, a crashed client) leaves one such query behind each time.

**UNITY-20261008-017.**
- `ApplicationImpl::desktopPath()` (`service/ApplicationImpl.cpp:86-104`) looks for `<id>.desktop` in
  `$XDG_DATA_DIRS/*/applications` only.
- The XDG base directory spec puts `$XDG_DATA_HOME` (default `~/.local/share`) before the data dirs, and gives
  `XDG_DATA_DIRS` the default `/usr/local/share:/usr/share` when it is unset. With it unset, this code splits ""
  into `[""]` and looks in `applications/` relative to the working directory.
- Qt has the spec's search as `QStandardPaths::locate(QStandardPaths::ApplicationsLocation, …)`.

**UNITY-20261008-018.**
- The message comes from QtDBus (`qdbusintegrator`) when a `NameOwnerChanged` for a watched name names an old
  owner that differs from the one QtDBus cached. It was seen once, in the bridge instance of the first boot after
  a VM restart, and not after the bridge was restarted (UNITY-20261008-011 logs/05).

## Reproduction (2026-10-09, target2, logs/01)

The setup: Clean-2, the live publication (hud +unity5, libcolumbus
+unity1, unity +unity13, u-s-d +unity13) and a cold cycle.

- **UNITY-20261008-025, reproduced.**
  - Five one-off `gdbus call … StartQuery "сохр" 3` clients, each its own
    bus connection that exits without `CloseQuery`, take hud-service from 0
    to 15 deleted mappings and its RSS from 30.2 to 38.9 MB. (The deleted
    mappings are only a side signal; they are not 5 × 3 Tries per query.
    The target check counts the exported query objects instead, see
    logs/02.)
    10 s later nothing is released.
  - A client that calls `StartQuery` and `CloseQuery` and stays 5 s is
    closed by the 2 s timer: no change.
  - With libcolumbus +unity1 a closed query frees its Tries, so what
    remains is exactly the queries hud-service still holds.
- **UNITY-20261008-017, reproduced.**
  - A GTK window with `application_id` `org.example.B017`, whose desktop
    file exists only in `~/.local/share/applications` (`Icon=utilities-terminal`),
    gets the stack id `org.example.B017`: bamf found the file.
  - The legacy `StartQuery` suggestions for it carry the icon `''`.
- **UNITY-20261008-018, reproduced, and harmless.**
  - The warning is in the journal of this boot as well: "QDBusConnection:
    name 'org.ayatana.bamf' had owner '' but we thought it was ':1.36'",
    at 04:12:35.18.
  - The order:
    - systemd starts bamfdaemon (28.56 s) and the bridge (28.63 s) in
      parallel;
    - the bridge's first bamf call asks dbus-daemon to activate
      `org.ayatana.bamf` (32.52 s);
    - bamfdaemon takes the name at 34.70 s;
    - the warning comes 0.5 s later.
  - `:1.36` **is** bamfdaemon (pid 2156), the owner of `org.ayatana.bamf`
    to this day. QtDBus had the right owner cached (it learned it while its
    call waited for the activation). The `NameOwnerChanged('', ':1.36')` of
    the acquisition arrived after that, and only its "old owner" field
    disagreed with the cache.
  - The bridge works afterwards: the stack has the B017 window with its id.
    A bamfdaemon restart while the bridge runs gives no warning, and the
    bridge keeps working.

## Design (for the Design Challenger)

**UNITY-20261008-025:**

- **The change:** `HudServiceImpl::closeQuery(path)` also removes the
  `m_legacyQueries` entry whose query has that path, stopping its timer.
  This is the path a `QueryImpl` takes when its sender leaves the bus
  (`serviceUnregistered` → `CloseQuery` → `closeQuery`), and also the
  timer's and `ExecuteQuery`'s path, which have already taken the entry.
- **Unchanged:** Unity 7's reuse of its legacy query while it stays on the
  bus, the 2 s timer after `CloseQuery`, and `ExecuteQuery`.
- **Test:** in `TestHudService` (the LegacyQuery fixture):
  - `StartQuery` from a sender, then `closeQuery(path)` as `QueryImpl` would
    call it;
  - then `openQueries()` is empty and the query is released (a `QWeakPointer`
    to the mock is null after the test drops its own reference);
  - the next `StartQuery` from the same sender creates a new query (the
    factory is called twice).

**UNITY-20261008-017:**

- **The change:** `ApplicationImpl::desktopPath()` uses
  `QStandardPaths::locate(QStandardPaths::ApplicationsLocation,
  "<id>.desktop")`. That is the XDG search: `$XDG_DATA_HOME/applications`
  (default `~/.local/share`) first, then `$XDG_DATA_DIRS/*/applications`
  (default `/usr/local/share:/usr/share`).
- **A behaviour change, per the spec:** a user's desktop file overrides a
  system one with the same id, so the HUD icon follows the user's override.
  (Round 1: the claim about bamf, the launcher and the Dash is reduced to
  what bamf's code shows.)
- **Tests (`TestApplication`):**
  - a desktop file only under a temporary `XDG_DATA_HOME` is found, with
    its icon;
  - a file of the same id under both, with different icons: the
    `XDG_DATA_HOME` one wins;
  - `XDG_DATA_DIRS` unset: no lookup relative to the working directory.
    The test runs from a directory with `applications/<id>.desktop` and
    expects it not to be found;
  - the existing `ReverseDnsIdPathAndIcon` stays.
  - The environment is restored after each test, unset as unset.
- **Also checked:** QStandardPaths' test mode is off in hud-service, so it
  reads the real paths.

**UNITY-20261008-018:**

- **No code change; closed as not a defect** (NOT_APPLICABLE, with this
  analysis), unless the Design Challenger finds a functional effect.
- **The alternative weighed:** order `window-stack-bridge.service`
  `After=`/`Wants=bamfdaemon.service`. It would remove the message, but
  bamfdaemon is a static, D-Bus-activated unit, and pulling it from the
  bridge's unit changes the session's start order for a log line. The
  bridge already retries nothing and needs nothing: QtDBus has the right
  owner.

**Target check (after APPROVE; Clean-2 + the live publication, then +unity6
from a file repository, a cold cycle; the same `repro.sh` before and after):**

- **025:** 5 one-off clients leave 15 mappings before; after, 0 within a
  few seconds. The StartQuery + CloseQuery client is unchanged.
- **017:** the legacy icon for the B017 window is `''` before and
  `utilities-terminal` after; Terminal's and Writer's icons are unchanged.
- **Regressions:**
  - Unity 7's HUD (opened, typed, closed, opened again: the same legacy
    query reused while Unity is connected);
  - a Writer HUD query;
  - the -001 move and the -011 ids (10 Writer starts, Terminal).

### Design review, round 1: REVISE (all points taken)

The Design Challenger (an independent subagent) confirmed the direction for
all three tasks. Its points, as applied below:

**UNITY-20261008-025:**

1. **`closeQuery(path)` is the path** taken when a legacy sender leaves.
   - The sender is the caller's unique name (`HudServiceImpl.cpp:91-97`).
   - The watcher is built before `StartQuery` replies.
   - `"local"` occurs only in tests, with mock queries.
2. **Null entries.**
   - `StartQuery` and `CloseQuery` read `m_legacyQueries[sender]` with
     `operator[]`, which inserts an empty `{null, null}` entry.
   - That happens at every Unity HUD activation that ends in an item:
     `ExecuteQuery` takes the entry, then Unity's hide sends `CloseQuery`
     (`unity hud/HudController.cpp:506`, `UnityCore/Hud.cpp:105-113`).
   - A search "by the query's path" that calls `path()` on such an entry
     would crash hud-service, and one-off senders that call `CloseQuery`
     without a query grow the map.
   - Revised: `CloseQuery` uses `find()` and inserts nothing, `StartQuery`
     uses `value()`, and the search in `closeQuery` skips null queries.
   - `closeQuery` keeps a strong reference to the query (`m_queries.take`
     into a local) while it removes the legacy entry.
   - Erasing the entry deletes its timer and any pending timer event. A
     `QTimer` deleted after its own `timeout` already happens today (the
     local `entry` in `legacyTimeout`).
   - **New for legacy queries:** they are now destroyed inside their own
     watcher's signal, as new-API queries already are. The target check
     shows hud-service survives it.
3. **Unity 7 is unaffected.**
   - Its `hud::Controller` and proxy live as long as compiz, on compiz's
     shared session connection, so its unique name stays the same.
   - It sends `CloseQuery` before every `StartQuery` (`UnityCore/Hud.cpp:217-225`).
     That is the timer's pattern, not `closeQuery`'s.
4. **The planned test could not pass.** `WillOnce(Return(query))` keeps a
   copy of the pointer in the expectation, so a weak pointer never expires.
   Revised:
   - the mock is created in an `Invoke` that keeps only a weak pointer (or
     `Return(ByMove(…))`), and the second `StartQuery` has its own mock;
   - one more case pins point 2: `ExecuteQuery`, then `CloseQuery` (it used
     to insert a null entry), then `StartQuery` and `closeQuery(path)`. No
     crash, and `openQueries()` is empty.
   - `TestQuery.CloseWhenSenderDies` already pins `QueryImpl` →
     `closeQuery(path)`.

**UNITY-20261008-017:**

5. **Qt 5.15 `QStandardPaths::locate(ApplicationsLocation)`:**
   - `$XDG_DATA_HOME` (else `$HOME/.local/share`) `/applications` first,
     then each XDG data dir (`/usr/local/share:/usr/share` when the variable
     is empty; empty and relative entries dropped);
   - the first regular file wins; no subdirectories; no caching; test mode
     is not enabled anywhere in hud.
   - **The card's claim that bamf, the launcher and the Dash "already do
     this" had no evidence.** Checked now in bamf 0.5.6 (`src/bamf-matcher.c:1142-1170`):
     it scans `XDG_DATA_HOME` and `~/.local/share/applications` before the
     system directories. Which of two files with the same id it finally
     picks also depends on its later matching (`:1736-1748`), so the card
     claims only the scan order.
   - **Where bamf's path and hud-service's lookup can still disagree:**
     bamf's `_BAMF_DESKTOP_FILE` hint and `--desktop_file_hint` (a path
     outside the XDG dirs), desktop files in subdirectories (`kde4-foo`),
     and a user file with `Hidden=true`. Asking the bridge for the path
     would change the WindowStack interface; these are known gaps.
6. **The tests are feasible.**
   - `qputenv`/`qunsetenv` work in-process because nothing is cached.
   - The old code really is cwd-relative when `XDG_DATA_DIRS` is unset, and
     a user service starts in `$HOME`, so it could read `~/applications`.
   - The cwd test sets `XDG_DATA_HOME` to an empty temporary directory, uses
     an id that cannot exist in the chroot, restores the working directory,
     and uses a fresh `ApplicationImpl` per case.

**UNITY-20261008-018:**

7. **NOT_APPLICABLE is right**, with corrected evidence:
   - **No signal is missed.** Qt 5.15 `serviceOwnerChangedNoLock` prints the
     message and then sets the cache to the new owner, which is the right
     one. Signal filtering uses that cache.
   - **What shows it:** the B017 window, opened after the warning, is in the
     stack. `m_windows` is filled only by `WindowPaths` at construction and
     by `ViewOpened`/`WindowAdded` (`BamfWindowStack.cpp:186-205`,
     `:240-246`), so bamf's signals arrived.
   - **The activation** comes from the bridge's explicit
     `isServiceRegistered`/`startService` (`BamfWindowStack.cpp:163-167`), not
     from "its first bamf call".
   - **The log:**
     - the 04:14:37 activation lines belong to the 018-bamf kill;
     - the `busctl` lines in logs/01 were taken after it, and the pre-kill
       ones (`:1.36` = pid 2156 bamfdaemon, the owner) are now recorded with
       that label;
     - the post-restart stack showed only compiz windows, so it does not
       prove the bridge kept working. The target check opens a window after
       a bamf restart.
   - **`After=`/`Wants=` is worse:** it would hold the bridge, and with it
     hud-service's window data, for the ~6 s bamf took to start, to remove
     one log line, and `Wants=` would pull in a static, D-Bus-activated
     unit.
   - **The existing report:** LP #1297471 (hud, Low, Confirmed, no fix),
     the same message with `':1.6'`.

**Existing fixes** (the DC also searched lp:hud r420 of 2020-03-16, which
our base includes; Ubuntu 0ubuntu1..6; GitLab and Lomiri; Debian, which has
no hud):

| task | existing fix | issue search |
|---|---|---|
| -025 | none | none; older hud-service memory reports (LP #967879, #1645186) name other causes |
| -017 | none | none |
| -018 | none, in hud or in Qt 5.15 | LP #1297471 |

8. **The target plan gets more steps** (below).

## Design, revised after round 1

**-025 (`service/HudServiceImpl.cpp`):**

- `StartQuery`: `m_legacyQueries.value(sender)`, so a missing entry is not
  inserted; the new query is stored as before.
- `CloseQuery`: `find(sender)`, so no entry is created. A found entry
  behaves as before: `UpdateQuery("")`, then the 2 s timer.
- `closeQuery(path)`:
  1. `Query::Ptr query(m_queries.take(path))`;
  2. then the `m_legacyQueries` entry whose query is non-null and has this
     path is erased, with its timer stopped first;
  3. return `query`.

**-017 (`service/ApplicationImpl.cpp`):** `desktopPath()` =
`QStandardPaths::locate(QStandardPaths::ApplicationsLocation, id + ".desktop")`.

**-018:** no code change; closed as NOT_APPLICABLE, citing LP #1297471.

**Tests:**

- `TestHudService`:
  - `LegacyQueryReleasedWhenSenderLeaves` (a weak pointer expires after
    `closeQuery`; the next `StartQuery` builds a new query);
  - `CloseQueryWithoutLegacyQueryAddsNothing` (`ExecuteQuery`, `CloseQuery`,
    `StartQuery`, `closeQuery`: no crash, `openQueries()` empty);
  - the existing `LegacyQuery` unchanged.
- `TestApplication`:
  - `DesktopFileInDataHome` (found, icon);
  - `DataHomeOverridesDataDirs`;
  - `NoCwdLookupWithoutDataDirs`.

**Target check** (Clean-2 + the live publication, then +unity6 from a file
repository, a cold cycle; before and after):

- **025:**
  - `OpenQueries` and the deleted mappings before and after five one-off
    `StartQuery` clients, then 10 s later;
  - a client with `StartQuery` + `CloseQuery` that exits inside the 2 s;
  - a client with `StartQuery` + `ExecuteQuery` that exits;
  - hud-service keeps its PID, and there is no coredump.
- **Unity 7's HUD:**
  - opened with a real Alt tap (vbox `send_keys`), with
    `dbus-monitor "interface='com.canonical.hud'"` running to see compiz's
    sender and the query key;
  - opened again within 2 s: the same query path; after more than 2 s: a
    new one;
  - an item run with Enter, then the HUD opened again: the
    `ExecuteQuery` + `CloseQuery` sequence of point 2;
  - `OpenQueries` holds at most one legacy path at a time.
- **017:**
  - the B017 window's legacy icon: `''` before, `utilities-terminal` after;
  - an override (a copy of `org.gnome.Terminal.desktop` in
    `~/.local/share/applications` with another `Icon=`): the HUD icon
    follows it, then the copy is removed;
  - Writer's icon is unchanged.
- **018:** after a bamfdaemon restart, a window opened then appears in the
  stack with its id.
- **Regressions:** 10 Writer starts (the -001 move), Terminal's id
  (UNITY-20261008-011).

### Design review, round 2: APPROVE

The revised design holds for all three tasks. Taken into the implementation:

1. **The -025 change is correct.**
   - `value()` in `StartQuery` is safe: its `else` branch only changes the
     objects the pointers point to.
   - `find()` in `CloseQuery` behaves as before for an existing entry and
     inserts nothing for a missing one.
   - `closeQuery` taking the query into a local, skipping null queries,
     stopping the timer and erasing has no re-entrancy problem.
   - A side benefit: a legacy client that calls `CloseQuery` on the query
     object itself now also removes its legacy entry.
2. **`LegacyQueryReleasedWhenSenderLeaves`:**
   - the mock built in the `Invoke` gets `ON_CALL(path())` and
     `ON_CALL(results())` with `ReturnRef` to objects that outlive it
     (`StartQuery` calls both, and a reference-returning mock has no
     default);
   - the second query has another path (`/path/query1`), so "new query" is
     seen in `openQueries()` too.
3. **`CloseQueryWithoutLegacyQueryAddsNothing`** must see the map itself:
   with `find()` a null entry never exists, and the null-skip in
   `closeQuery` would hide a regression. A test subclass exposes the size
   of the protected `m_legacyQueries`, which must be 0 after a bare
   `CloseQuery` and 0 after `ExecuteQuery` + `CloseQuery`.
4. **`NoCwdLookupWithoutDataDirs`** sets `XDG_DATA_HOME` explicitly, so the
   sbuild `HOME` is never used.
5. **bamf's scan order**, as the card states it, is correct. The final
   order is the Desktop folder, `~/.local/share/applications`,
   `$XDG_DATA_HOME`, `/usr/local/share`, `/usr/share`, then the
   `XDG_DATA_DIRS` entries, with subdirectories after their parent. Two
   more divergences from Qt, both known gaps and not regressions:
   - bamf reads `XDG_DATA_DIRS` in reverse order (`bamf-matcher.c:1120-1126`
     prepends each), so for an id in two system directories bamf and hud
     may pick different files;
   - bamf always scans `~/.local/share/applications`, even when
     `XDG_DATA_HOME` points elsewhere; Qt looks only in `$XDG_DATA_HOME`.
6. **`dbus-monitor "interface='com.canonical.hud'"` drops method returns**,
   and with them the query key in `StartQuery`'s reply. The query path is
   taken from Unity's `CloseQuery` argument (`UnityCore/Hud.cpp:190-193`) or
   from the `OpenQueries` property.
7. **The "StartQuery + ExecuteQuery" client:**
   - it must use an integer key from its own suggestions, with a window
     focused, and a harmless item;
   - two existing paths through `ExecuteQuery` could crash hud-service: a
     key that is not an integer (`QueryImpl::ExecuteCommand` calls
     `sendErrorReply` outside a D-Bus call) and no focused window
     (`m_windowToken` null, `QueryImpl.cpp:134`);
   - both are older than this revision and are not part of -025: a
     follow-up candidate for C (now UNITY-20261009-003).
8. **The rest of the target plan is enough.**

## Implementation (2026-10-09)

hud source `packages/hud`, branch `b/UNITY-20261008-025` (pushed), on the
published +unity5 (`db26b0d`):

- `327ddb9`, the tests:
  - `TestHudService`: `LegacyQueryReleasedWhenSenderLeaves` (the query of a
    vanished sender is released and a new `StartQuery` gets a new query on
    another path) and `CloseQueryWithoutLegacyQueryAddsNothing` (through a
    test subclass that exposes the size of `m_legacyQueries`: 0 after a bare
    `CloseQuery`, 0 after `ExecuteQuery` + `CloseQuery`);
  - `TestApplication`: `DesktopFileInDataHome`, `DataHomeOverridesDataDirs`,
    `NoCwdLookupWithoutDataDirs` (each with its own `XDG_DATA_HOME` and
    `XDG_DATA_DIRS`, never the build's `HOME`).
- `ffa23e3`, -025: `HudServiceImpl::closeQuery` also removes the legacy
  entry whose query has that path, stopping its timer. That is the path
  `QueryImpl` takes when its sender leaves the bus. `StartQuery` reads the
  map with `value()` and `CloseQuery` with `find()`, so a sender without a
  query no longer gets an empty entry.
- `68a61fe`, -017: `ApplicationImpl::desktopPath` uses
  `QStandardPaths::locate(ApplicationsLocation, <id>.desktop)`, the XDG
  search with `XDG_DATA_HOME` first.
- `1369d9e`: changelog `14.10+17.10.20170619-0ubuntu6+unity6`.

-018 is NOT_APPLICABLE (see Reproduction), so it has no code.

**Builds** (`build_sbuild.py`, chroot 20261008T083223Z; logs/04):

- +unity6 (`1369d9e`): 6 of 6 suites pass; the service suite has 51 tests,
  among them the 5 new ones.
- control (`327ddb9`: the tests only, on the +unity5 code, a local branch
  `control/UNITY-20261008-025`): the service suite fails exactly the 5 new
  tests (46 of 51 pass), and the other 5 suites pass:
  - the 3 `TestApplication` tests give an empty desktop path, the system
    icon over the user override, and `./applications/...` found relative to
    the working directory;
  - the 2 `TestHudService` tests keep one legacy entry, after the sender
    left and after a bare `CloseQuery`.

  The first control attempt never reached the tests: snapshot.ubuntu.com
  answered 502/503 while the build dependencies were being installed. It
  was rerun the same day, once the same URL answered 200.

## Target check (target2, 2026-10-09, logs/02, logs/03)

Each measurement starts from a cold boot (`systemctl poweroff` over ssh,
then `start_vm`), never a reboot from inside the guest. Clean-2 was restored
and confirmed from inside the guest before each stack:

- no `~/.dirty`;
- no work directories;
- only `ubuntu.sources`;
- hud `0ubuntu6`.

Then came `apt full-upgrade` from the live archive, and for "after", hud
+unity6 from this task's build (the .deb sha256 `9fafa7227344aa06...`;
`apt` upgraded only hud). The running `hud-service` was checked against the
installed binary (sha256 `3471e07f522bfd36`, no `(deleted)` mappings).

**-025 and -017, the same script before and after (`target025.sh`, logs/02):**

| | +unity5 | +unity6 |
|---|---|---|
| query objects after 5 one-off `StartQuery` clients | 5 | 0 |
| the same 10 s later | 5 | 0 |
| query objects at the end of the run | 8 | 0 |
| `StartQuery` + `CloseQuery` client, `StartQuery` + `ExecuteQuery` client | released | released |
| hud-service restarts (the same PID through the run) | none (3690) | none (3617) |
| icon of a user-only desktop file (B017) | `''` | `utilities-terminal` |
| icon of Terminal with a user override `Icon=b017-override` | `org.gnome.Terminal` | `b017-override` |
| icon of Writer (system desktop file only) | `libreoffice-writer` | `libreoffice-writer` |
| -018: id of a Terminal opened after a bamfdaemon restart | `org.gnome.Terminal` | `org.gnome.Terminal` |

**The Unity 7 HUD, driven like a user (`hud-alt.sh`, logs/03):**

- Alt is a real keyboard event (vbox `send_keys`). The query is typed with
  xdotool, and Unity's calls are captured with dbus-monitor.
- There is one legacy query per sender:
  - a reopening within 2 s of `CloseQuery` keeps its path (query/11 for
    "о" → "он" → "оно");
  - after more than 2 s a reopening gets a new one (query/10 → query/11).
- Enter: `ExecuteQuery` releases the query. Unity's `CloseQuery` right
  after it changes nothing, and no query objects are left.
- hud-service kept its PID through each +unity6 run: 3910 in run 2, and
  3757 in run 4 together with the regression steps. Run 1 followed
  `target025.sh` in the same boot. Run 3 is the base package.

**Regressions (UNITY-20260929-001 `target.sh` on +unity6, logs/03):**

- Writer started 10 times: the window stack gives `libreoffice-writer` every
  time.
- «Сохранить» through the HUD is recorded under `libreoffice-writer`, and it
  is the first row of the empty HUD after a restart.
- A Terminal gets `org.gnome.Terminal` from the bridge.
- The usage table records the Unity 7 HUD's Terminal command under
  `org.gnome.Terminal`; the base `0ubuntu6` recorded it under `org`.

**Seen, not caused by this revision (UNITY-20261009-004):** «Создать окно»
for gnome-terminal through the HUD opens no window:

- the item is found, and Unity sends `ExecuteQuery` and `CloseQuery`;
- the same happens on the Ubuntu base `0ubuntu6`, with the same calls and
  the same hud-service log lines;
- the legacy `ExecuteQuery` path is not in this diff.

## Verification (independent Verifier, 2026-10-09): PASS

The Verifier did not write the fix. Review status:
INDEPENDENTLY_REPRODUCED, on target2 with hud +unity6.

- **The code against the round-2 design** (`git diff db26b0d 1369d9e`):
  - **Scope:** exactly five files changed: the two sources, the two test
    files and `debian/changelog`.
  - **`closeQuery`:** the query is held until return. The loop compares
    the path and stops the timer, then erases and breaks; nothing touches
    the erased iterator afterwards. At most one entry can match, since
    paths are unique.
  - **`value()` and `find()`:** `value()` in `StartQuery` and `find()` in
    `CloseQuery` behave as designed.
  - **`ExecuteQuery` and `legacyTimeout`:** both take the entry before they
    call `closeQuery`. There is no double stop and no early release.
  - **A sender leaving the bus:** `QueryImpl::serviceUnregistered` →
    `closeQuery` destroys the query inside its watcher's signal, as
    new-API queries already did. In Qt 5.15 that is the last emission, and
    hud-service survived a live client that left with its 2 s timer
    pending.
  - **The desktop-file lookup:**
    - `QStandardPaths::locate(ApplicationsLocation)`, read in the Qt 5.15
      source, searches `XDG_DATA_HOME` first, then `XDG_DATA_DIRS`, with
      the spec's defaults;
    - empty and relative `XDG_DATA_DIRS` entries are dropped, so the
      working directory is never searched;
    - a grep of the whole tree finds no other runtime desktop-file lookup.
- **Tests:**
  - The control fails exactly the 5 new tests (service 46/51, every other
    suite passes), each with the expected message. None passes vacuously.
  - +unity6 passes 6/6 (service 51).
  - The control is also the "no erase in `closeQuery`" mutant. Reverting
    `find()` in `CloseQuery` is caught by
    `CloseQueryWithoutLegacyQueryAddsNothing`.
  - `ScopedEnv` restores the environment. The new tests set
    `XDG_DATA_HOME` themselves; sbuild's `HOME` is `/sbuild-nonexistent`.
- **Provenance:**
  - the manifest's commit and tree equal `1369d9e`, and all 24 artifacts
    match their sha256 and size;
  - `dpkg-source -x` of the `.dsc` equals `git archive 1369d9e`. The only
    extra is an empty locale directory tree in the orig tarball, which git
    cannot track;
  - the changelog trailer is in UTC, with author NeiroNext and no
    `Signed-off-by`;
  - `hud-service` from the built `.deb` has sha256 `3471e07f522bfd36`.
- **target2:**
  - **The running binary:** the running hud-service (PID 3757) is the
    installed file, which is the build's (`dpkg --verify` clean, 0
    `(deleted)` mappings).
  - **-025:** 8 one-off `StartQuery` clients leave 0 query objects (the
    ids advanced by 8: created and released). Adversarial clients, each on
    its own connection:
    - one leaving inside its 2 s timer;
    - one bare `CloseQuery`;
    - reuse, then `CloseQuery` on the query object, then a new path;
    - two senders at once, each erased on its own;
    - the timer releasing a query.
    All ended at 0 objects, with the same PID throughout.
  - **-017:** a desktop file only in `~/.local/share/applications` gives
    the window its id, its icon and its `DesktopPath`.
  - **The usage table's timeline** (dpkg.log, journal, hudmon) confirms
    that the `org` row was written by the base package only.
- **The card's numbers** match logs/01-03 and the hudmon captures.

Remarks:

1. Qt 5.15 does not reject a relative `XDG_DATA_HOME`. With one,
   `desktopPath()` could return a path relative to the working directory;
   the spec says such a value is ignored. The session does not set
   `XDG_DATA_HOME`. Follow-up UNITY-20261009-005.
2. "coredumps 0" in `target025.sh` proved nothing (coredumpctl is not
   installed on target2). The evidence is the unchanged PID; the card says
   so now.
3. The deleted mappings are only a side signal (not 5 × 3 Tries per
   query); the card now says so.
4. Two existing tests, `ReverseDnsIdPathAndIcon` and
   `DBusInterfaceIsExported`, now also look in
   `$HOME/.local/share/applications`. This is harmless under sbuild
   (`HOME=/sbuild-nonexistent`).
5. The unit tests use one sender, so an erase of the wrong sender's entry
   would pass them. The live two-sender client on target2 covers that
   case.

Not run: a rebuild, or a local run of the unit tests (the sbuild logs were
used instead); a real Alt in the Unity 7 HUD (logs/03 was used instead);
the base reproduction of UNITY-20261009-004; the -018 bamfdaemon restart.

## Known gaps

| gap | where it is covered |
|---|---|
| bamf and hud-service can still pick different desktop files: bamf always scans `~/.local/share/applications` even when `XDG_DATA_HOME` points elsewhere, reads `XDG_DATA_DIRS` in reverse and searches subdirectories. | design review round 2, point 5; not a regression, both differ from Qt the same way as before |
| A relative `XDG_DATA_HOME` is not ignored by Qt 5.15. | UNITY-20261009-005; not set in the Unity session |
| Two crash paths of the legacy `ExecuteQuery`: a key that is not an integer, and no focused window. | UNITY-20261009-003 (older than this revision) |
| The Unity 7 HUD command «Создать окно» for gnome-terminal opens no window; the same on the Ubuntu base. | UNITY-20261009-004 |
| An Ubuntu upload of hud would replace +unity6 without these fixes. | the usual risk of a carried package; hud upstream inactive since 2020 |
