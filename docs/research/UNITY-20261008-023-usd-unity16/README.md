# UNITY-20261008-023: unity-settings-daemon +unity16 (presence idle in the Unity session)

Agent A, target `target-desktop`. One of three changes published together:
unity-settings-daemon +unity16 (this task), cinnamon-session +unity7
(UNITY-20261013-016, the idle delay from the Unity Control Center) and
light-locker +unity4 (UNITY-20261013-018, application inhibitors reach the
session manager).

## What was wrong

cinnamon-session, the Unity session's session manager, never marked the
session idle: its presence watches the user's idle time through
libcinnamon-desktop's idle monitor, a client of
`org.cinnamon.Muffin.IdleMonitor`, and nothing in the Unity session owned
that name (Muffin is Cinnamon's window manager). unity-settings-daemon
serves the same monitor as `org.gnome.Mutter.IdleMonitor`.

## What is fixed

| package | version | change |
|---|---|---|
| unity-settings-daemon | 15.04.1+21.10.20220802-0ubuntu7+unity16 | Commits on the published +unity15 (`2d0e9bf`), branch `a/UNITY-20261008-023`, in `gnome-settings-daemon/`. |

- `dcd7ea9`: in a Unity session (`XDG_CURRENT_DESKTOP`), the idle monitors
  are also exported under `org.cinnamon.Muffin.IdleMonitor`
  (`/org/cinnamon/Muffin/IdleMonitor`, `Core` and `Device<n>`), the same
  monitors and watches as the Mutter interface. The name is taken only
  when Muffin does not hold it. `WatchFired` goes to the client that added
  the watch, on the object and interface it came through; through this
  interface a client removes only its own watches. The Mutter interface is
  unchanged.
- `8b8c6da`, `04963c7`, `32ba40e`, `82e9267`: tests (`test-idle-monitor-dbus`,
  `test-idle-monitor-registry`), run by `make check` under xvfb on a
  private session bus.
- `c02cf52`: changelog; `Breaks: cinnamon-session (<< 6.4.2-1+unity7)`, so
  that the idle monitor does not arrive without the cinnamon-session that
  takes its delay from the Control Center.

There is no library or ABI change.

## Checks

- **Tests:** on +unity15 with the new tests, the five cases of the Muffin
  interface fail at the wait for its name; the Mutter case and the
  "not outside Unity" case pass on both.
- **Target, this change alone** (`dev/target-change1/`): cinnamon-session
  adds its watch through the new interface, the session goes idle after
  the delay and Unity's lock screen appears, input brings it back, a
  restart of unity-settings-daemon is followed by the watch being added
  again. Video players' screensaver inhibitors did not reach the session
  manager - fixed by light-locker +unity4 (UNITY-20261013-018).

## Verification

- Target test before publication: PASS (`gate/target-test.txt`).
- Check on the target after publication, of the whole series: PASS.
  Published 2026-10-13 19:56:20Z as `unity-resolute-20261008-023`; the
  target restored and updated from the live repository (u-s-d +unity16,
  cinnamon-session +unity7, light-locker +unity4), cold boot: the session
  goes idle and locks after the Control Center's delay; while VLC plays it
  does not go idle; without an inhibitor it goes idle and locks as before
  (`gate/target-verification.txt`).
- Independent verification: PASS.

## Not changed / known limits

- The power plugin's screen blanking follows light-locker's activation,
  not the session's idle state.
- Known lifecycle issues of the device monitors in `gsd-idle-monitor.c`
  are left as they are.

## Publication

- **Database backup:** `/home/claude/backups/UNITY-20261008-023-20261013T191159Z`.
  21 files, complete, equal to live; list sha256
  `7703b614421c2d10582e55c959287844a538bb99026e5985b7425590a80692c5`.
- **Repository:** 8 records added to `unity-resolute` (the source, 5 .deb
  and 2 .ddeb); the sha256 of every pool file matches the build manifest.
- **Snapshot:** `unity-resolute-20261008-023`, which is the live
  `unity-resolute-20261013-018` plus these 8 records
  (`gate/snapshot-diff.txt`). cinnamon-session 6.4.2-1+unity7 is in it,
  so the new Breaks resolves.
- **Version safety:** SAFE (`gate/version-check.json`,
  `gate/version-safety.json`).
- **Peer notice:** agent B, ACK.
