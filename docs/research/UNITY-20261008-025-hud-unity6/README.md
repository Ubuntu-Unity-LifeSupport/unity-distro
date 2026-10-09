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
    to 15 deleted mappings (5 × 3 Tries) and its RSS from 30.2 to 38.9 MB.
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
  This is what bamf, the launcher and the Dash already do.
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
