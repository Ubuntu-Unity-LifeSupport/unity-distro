# UNITY-20261013-016, UNITY-20261013-020, UNITY-20261013-022: cinnamon-session +unity7

Agent A, target `target-desktop`. Part of UNITY-20261008-023 (presence idle in
the Unity session), published before light-locker +unity4
(UNITY-20261013-018) and unity-settings-daemon +unity16 (UNITY-20261008-023).

## What is fixed

| package | version | change |
|---|---|---|
| cinnamon-session | 6.4.2-1+unity7 | Commits on the published +unity6 (`7904214`), branch `a/UNITY-20261013-016`. |

- `f1fed77` (-016), `d/p/Take-the-idle-delay-from-the-Unity-Control-Center-in-a-Un.patch`:
  in a Unity session the presence's idle delay follows
  `org.gnome.desktop.session idle-delay`, the setting of the Unity Control
  Center, live; elsewhere `org.cinnamon.desktop.session` as before. 0 still
  means never.
- `7390fb0` (-020), `d/p/Take-the-session-s-logind-inhibitor-in-block-weak-mode.patch`,
  upstream PR linuxmint/cinnamon-session#219 (not merged yet): the logind
  lock cinnamon-session takes for applications' suspend inhibitors is taken
  in `block-weak` mode where logind supports it. Since systemd 257 a
  `block` lock also applied to the session itself: logind answered
  "challenge" to CanSuspend, CanReboot and CanPowerOff while an application
  inhibited suspend. resolute's gnome-session already takes its lock this
  way.
  - Idle suspend still honours the inhibitors: unity-settings-daemon checks
    the session manager's `InhibitedActions` before it arms the sleep
    timeout.
  - A suspend the user asks for (Unity's dialog, the session indicator, the
    suspend key) is no longer refused while an application inhibits
    suspend, as before systemd 257. Unity's Suspend button, the indicator's
    restart and power off, and the critical battery action work again in
    that case.
- `2f6694e` (-022), `debian/dbus-override.service.conf`: a drop-in for the
  user `dbus.service` with `OOMPolicy=continue`, as upstream 2605e63 and
  c038bb4, so that a kernel OOM kill of a program D-Bus started does not
  stop the session bus. It is installed in
  `/usr/lib/systemd/user/dbus.service.d/` and applies to every user's
  `dbus.service` on the machine.
- `954e756`: changelog.

UNITY-20261013-021 (upstream 51cb449) was checked and does not apply: it
changes the ConsoleKit backend only; the Unity session runs under logind.

## Checks

- **-016 on target:** with the Control Center delay at 60 s and Cinnamon's at
  600 s, the session went idle and locked after about 60 s; the delay set
  to 0 while running kept it from going idle; a new cinnamon-session start
  asks the idle monitor once.
- **-020 on target:** with one or two applications holding suspend
  inhibitors, the lock is `block-weak`, the session manager reports the
  suspend inhibition, and logind answers "yes" to CanSuspend, CanReboot and
  CanPowerOff (with +unity6: "challenge"); the lock goes with the last
  inhibitor.
- **-022 on target:** after a new login `OOMPolicy` of the user
  `dbus.service` is `continue` (was `stop`), the drop-in is listed, and no
  other property of the unit changed.
- cinnamon-session has no test suite for these paths.

## Not changed / known limits

- The drop-in of -022 has no effect on the main dbus-daemon process itself
  being killed.
