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
