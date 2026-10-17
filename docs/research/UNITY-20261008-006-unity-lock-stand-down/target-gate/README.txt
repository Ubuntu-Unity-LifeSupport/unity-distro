UNITY-20261008-006: target test of the gated builds - light-locker 1.8.0-3ubuntu4+unity5 (build-ll-gate/) and
unity 7.7.1+26.04.20260306-0ubuntu3+unity14 (build-unity/) together. Times EEST on the target, 2026-10-17.

Target: target-desktop restored from Published-stack-2026-10-08 (boot 09:12:50; light-locker +unity2, unity +unity12
and unity-settings-daemon +unity11 from the snapshot), apt-get update and full-upgrade from the live repository:
cinnamon-session 6.4.2-1+unity8, libgtk-nocsd0 4.8-1+unity5, unity-gtk4-menu 0.13, light-locker +unity4, unity +unity13,
unity-settings-daemon +unity16; nothing left to upgrade (01). xdotool, wmctrl and vlc installed for the checks. Then
light-locker_1.8.0-3ubuntu4+unity5_amd64.deb (sha256 d0440fb6...) and unity_7.7.1+26.04.20260306-0ubuntu3+unity14_amd64.deb
(daaee924...), libunity-core-6.0-9 (832b15d5...), unity-schemas (26c923fb...), unity-services (8bdbf34d...), unity-uwidgets
(9c079ff2...) of +unity14, light-locker first; nothing removed (02). During the boots unattended-upgrades removed old
kernel packages (linux-*-7.0.0-14); nothing of the session.

Start-up (names.sh: owner and queue of both ScreenSaver names, start times):
- 03-07, five cold boots: light-locker owns org.gnome.ScreenSaver every time, compiz (Unity) queued behind it.
  org.freedesktop.ScreenSaver: light-locker with unity-settings-daemon queued on boots 1, 3, 4, 5; on boot 2
  unity-settings-daemon (its screensaver proxy) had it and light-locker still started and owns org.gnome.ScreenSaver.
- 08 and 10, forced order (~/.config/autostart/light-locker.desktop with X-GNOME-Autostart-Delay=20, removed
  afterwards): light-locker started 30 s after unity-settings-daemon; org.freedesktop.ScreenSaver owned by
  unity-settings-daemon, light-locker not in its queue; org.gnome.ScreenSaver light-locker, compiz queued. The checks in
  that state were run twice; the raw files of the first run (08, ~09:44) were deleted on the target before they were
  copied, so the records are those of the second run (10, 10:40-10:45, forced/): F1 Ctrl+Alt+L, F2
  light-locker-command -l (goes through the proxy) and F3 presence idle (idle-delay 20, lock-delay 0) each lock
  through light-locker (one LockSession, one SetLockedHint, greeter on VT 8); F4b, a client holding an
  org.freedesktop.ScreenSaver Inhibit: the call went to unity-settings-daemon, the session manager held an idle
  inhibitor (IsInhibited(8) true), the session did not go idle or lock in 40 s with idle-delay 20; after release no
  inhibitor. (In the first run an F4 with VLC playing an audio file took no inhibitor - VLC inhibits for video.)
- 09, final cold boot without the override: light-locker owns both names; the running light-locker is the installed
  binary (exe sha256 3ad3c7b4...).

Trigger table on that boot (final.sh: runall.sh, second.sh, suspend, restart.sh; SUMMARY.txt): for each run, the state
12 s after the trigger, the LockSession calls on the system bus (LightDM's, plus loginctl's own in 04/08), SetLockedHint
calls, Unity's Locked signals, and calls of org.gnome.ScreenSaver SetActive/Lock on the session bus.
| run | trigger | result |
|---|---|---|
| 01 | Super+L | Unity LockRequested, then Lock to light-locker; greeter, one SetLockedHint, Unity not locked |
| 02 | com.canonical.Unity.Session.Lock | as 01 |
| 03 | Ctrl+Alt+L | light-locker locks, one SetLockedHint |
| 04 | loginctl lock-session | light-locker locks; Unity sends no LockRequested and does not lock |
| 05 | presence idle, idle-delay 20, lock-delay 0 | SetActive(true) then Lock, light-locker locks |
| 05b | idle (idle-delay 20), lock-delay 30, input 30 s after the trigger (about 15 s into the lock-delay) | SetActive(true) on each idle, no Lock, not locked |
| 05c | idle continuing from 05b (no input), lock-delay 30 | Lock after the delay, light-locker locks (the SetActive came in 05b) |
| 05d | idle, lock-enabled false | SetActive(true) only, GetActive true (blank), not locked |
| 06 | legacy mode (screen-keyboard-enabled), Super+L | Lock to light-locker, locked |
| 07 | legacy mode, presence idle | SetActive(true) and Lock, light-locker locks (before the change nothing locked) |
| 08 | legacy mode, loginctl lock-session | light-locker locks, Unity does not |
| 09 | suspend (systemctl suspend from the user manager) | request 10:03:04, sleep 10:03:05 (before the change 30 s); no inhibitor timeout; on resume the greeter (light-locker), Unity not locked; woken with a key from the host |
| 12 | a second light-locker while the first owns the names | exits "screensaver already running", no SetLockedHint, the first keeps both names |
| 13 | light-locker killed | compiz (Unity) owns org.gnome.ScreenSaver, unity-settings-daemon org.freedesktop.ScreenSaver; light-locker started again exits "already running", no SetLockedHint |
| 13b | Super+L after that | Unity's own lockscreen locks, one SetLockedHint from Unity |
In every run of the table Unity's lockscreen target stayed inactive and no Locked signal came from Unity, except 13b
where Unity is the locker.

Not shown here: DPMS (unity-settings-daemon does not blank inside a VM), a lid, a guest account, switch-user from the
indicator, and logins after the first in a session (each boot is a cold boot). The Breaks of unity +unity14 against
light-locker << +unity5 was measured on 2026-10-17 before the L2 rebuild (../target/02-breaks-check.txt): without
light-locker +unity5 available apt removes light-locker and light-locker-settings to install unity +unity14.

Result: PASS.
