# UNITY-20261013-018: light-locker +unity4 (application inhibitors reach the session manager)

Agent A, target `target-desktop`. Part of UNITY-20261008-023 (presence idle in
the Unity session), published after cinnamon-session +unity7 and before
unity-settings-daemon +unity16.

## What was wrong

light-locker owns `org.freedesktop.ScreenSaver` in the Unity session, the
name video players and browsers (VLC, Firefox) use to keep the screen on
while they play. It kept those inhibitors to itself: they stopped only its
own activation. The session manager never heard of them, so once the
session's idle presence works, the session would go idle, blank and lock
during playback.

## What is fixed

| package | version | change |
|---|---|---|
| light-locker | 1.8.0-3ubuntu4+unity4 | Patches on the published +unity3 (`07367c0`), branch `a/UNITY-20261013-018`. |

- `d/p/0006-Forward-ScreenSaver-inhibitors-to-the-session-manage.patch`:
  each inhibitor an application takes through `org.freedesktop.ScreenSaver`
  is also taken from `org.gnome.SessionManager` as an idle inhibitor (as
  gnome-screensaver 2.x did) and released with it - on UnInhibit and when
  the application goes away. A caller now counts as gone only when its own
  bus connection goes away; before, an application that took or dropped one
  of its other bus names lost its inhibitor.
- `d/p/0007-Test-ScreenSaver-inhibitors-as-the-session-manager-s.patch`:
  `test-listener-inhibit` in `make check`; `Build-Depends: dbus-daemon
  <!nocheck>` for it (test only).

## Checks

- **Tests:** on +unity3 with the new test, the forwarding cases and the
  bus-name case fail; on +unity4 all pass.
- **Target** (with unity-settings-daemon +unity16): while VLC or Firefox
  play, their inhibitors are held by the session manager and the session
  does not go idle; closing or killing the player releases them; without an
  inhibitor the session goes idle and locks as before; a manual lock during
  playback still locks.
