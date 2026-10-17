UNITY-20261008-006: which locker locks the Unity session today, per trigger (target-desktop, 2026-10-13,
times EEST)

Stack: the live published repository - unity 7.7.1+26.04.20260306-0ubuntu3+unity13, light-locker
1.8.0-3ubuntu4+unity4, unity-settings-daemon +unity16, cinnamon-session 6.4.2-1+unity7, lightdm
1.32.0-6ubuntu4+unity2, indicator-session 0ubuntu5+unity1, unity-session 49.4+unity2. Session 3 on VT 7.
light-locker (PID 2740) owns org.gnome.ScreenSaver throughout. X: screensaver timeout 0, DPMS 0/0/0.
On the session bus Unity is :1.97, light-locker :1.89; on the system bus Unity (compiz) is :1.72, light-locker
:1.65, LightDM :1.17.
Each run (lk.sh, show.sh): state before and 2, 5 and 12 s after the trigger (VT in front, LockedHint, Active,
IdleHint, org.gnome.ScreenSaver GetActive, X monitor state), system and session bus traffic, user journal.
Between runs the session was unlocked with loginctl unlock-session (and chvt 7 when the greeter was in front).
idle-delay was 0 (idle off) except in the idle runs.

| run | trigger | who locked | observed |
|---|---|---|---|
| 01 | Super+L (xdotool) | Unity | Unity LockRequested, Locked; SetLockedHint(true) from Unity; VT 7; GetActive false (light-locker) |
| 02 | com.canonical.Unity.Session.Lock (the call indicator-session makes while Unity is on the bus) | Unity | as 01 |
| 03 | Ctrl+Alt+L | light-locker | u-s-d calls org.gnome.ScreenSaver.Lock; light-locker ActiveChanged, SetLockedHint(true); 4 s later LightDM LockSession, greeter on VT 8. Unity's lockscreen target stays inactive |
| 04 | loginctl lock-session | light-locker | Unity sends LockRequested but no Locked, its lockscreen target stays inactive; light-locker ActiveChanged, SetLockedHint(true); greeter on VT 8 after 10 s |
| 05 | presence idle (idle-delay 20) | Unity | StatusChanged idle at +15 s; 10 s later Unity ActiveChanged (blank), 0.5 s later LockRequested, Locked, SetLockedHint(true) from Unity; VT 7; X monitor stays "On"; light-locker GetActive false |
| 06 | legacy mode (screen-keyboard-enabled true), Super+L | light-locker | Unity LockRequested, then Unity calls org.gnome.ScreenSaver.Lock; light-locker locks, greeter on VT 8 |
| 07 | legacy mode, presence idle (idle-delay 20) | nobody | StatusChanged idle and IdleHint yes; 16 s later still unlocked, nothing from Unity or light-locker |
| 08 | legacy mode, loginctl lock-session | light-locker | Unity LockRequested and org.gnome.ScreenSaver.Lock; light-locker locks, greeter on VT 8 |
| 09 | suspend (systemctl suspend from the user manager) | both | PrepareForSleep(true) 23:41:26.6; Unity Locked and SetLockedHint(true) 2.9 s later; light-locker ActiveChanged at +12 s; logind: "Delay lock is active (UID 1000/mike, PID 2740/light-locker) but inhibitor timeout is reached", sleep began at 23:41:56.7 (30 s after the request). On resume (woken by a key; the RTC alarm did not wake the guest) LightDM LockSession, greeter on VT 8, Unity's lockscreen still active on VT 7 |

Sleep delay inhibitors before run 09 (systemd-inhibit --list): compiz "Unity needs to lock the screen",
unity-settings-daemon "GNOME needs to lock the screen", light-locker; all delay mode.

Legacy-mode recovery: after run 08, switching back to VT 7 brought the greeter back several times (new greeter
sessions in the lightdm journal) until legacy mode was turned off; the sequence was not traced. After it was
turned off, chvt 7 gave Unity LockRequested and UnlockRequested 20 ms apart and an unlocked session.

The apport dialog visible after resume belongs to two crash files present in the snapshot (10:30); no new file.
