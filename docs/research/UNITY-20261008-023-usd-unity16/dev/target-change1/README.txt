UNITY-20261008-023: target run of change 1 alone (unity-settings-daemon 15.04.1+21.10.20220802-0ubuntu7+unity16,
dev build of 32ba40e - not the gate build), 2026-10-13. Times EEST on the target.

Setup (01-install.txt): target-desktop on the live stack (u-s-d +unity15, compiz +unity3, cinnamon-session
6.4.2-1+unity5, light-locker 1.8.0-3ubuntu4+unity3). The three +unity16 debs installed with
dpkg -i --force-breaks (the new Breaks: cinnamon-session (<< 6.4.2-1+unity7) is not satisfiable until
UNITY-20261013-016); cold boot. Without change 2, cinnamon-session takes its delay from
org.cinnamon.desktop.session idle-delay, set to 60 for runs A/B/C and reset to the default (900) afterwards.
dbus-monitor on the session bus recorded the Muffin interface, Presence signals and Inhibit calls
(monitor-muffin-presence.log, monitor-inhibit.log). Observation script output in 02-09.

Boot (02-boot.txt): org.cinnamon.Muffin.IdleMonitor and org.gnome.Mutter.IdleMonitor owned by
unity-settings-daemon (the dev build's binary); org.gnome.ScreenSaver and org.freedesktop.ScreenSaver by
light-locker; presence available.

Run A (03-05): last input 14:37:45; cinnamon-session removed its startup watch and added
AddIdleWatch(60000) through org.cinnamon.Muffin.IdleMonitor; at 14:38:45 WatchFired (unicast to
cinnamon-session), Presence StatusChanged 3, AddUserActiveWatch; logind IdleHint yes; then Unity's lock
screen (session stays active on tty7, LockedHint yes; light-locker GetActive false - not light-locker).
loginctl unlock-session, then input: StatusChanged 0 on the input, IdleHint no.
Run B (06): systemctl --user restart unity-settings-daemon: the new process owns both names;
cinnamon-session added AddIdleWatch(60000) again on its own; 60 s later WatchFired, StatusChanged 3.
Run C1 (07): gnome-session-inhibit --inhibit idle: inhibitor listed by cinnamon-session; no idle after
80 s without input.
Run C2 (08): VLC 3.0.23 playing a video in a loop: VLC calls org.freedesktop.ScreenSaver.Inhibit
("vlc", playback), which light-locker owns; cinnamon-session lists no inhibitor; after 80 s without
input presence idle, IdleHint yes, LockedHint yes, the screen blanked (screenshot black from inside and
from the host) during playback.
Run C3 (09): snap Firefox 149 playing a local video: Firefox calls org.freedesktop.ScreenSaver.Inhibit
("firefox_firefox") as well, UnInhibit when the short video ended; no inhibitor at cinnamon-session.
The idle outcome of this run is not conclusive (idle time was reset during the run: 39 s at t+80 s).

light-locker (packages/light-locker src/gs-listener-dbus.c): Inhibit/UnInhibit on org.freedesktop.ScreenSaver
are kept in light-locker's own inhibitor list (they stop only its own lock); nothing is passed to
org.gnome.SessionManager.

Result: change 1 works as designed (Muffin name, watches, WatchFired routing, restart, session-manager
inhibitors). Finding for the product (I6): applications' screensaver inhibitors (VLC, Firefox) do not
reach cinnamon-session in the published configuration, so with idle working the Unity session blanks and
locks during video playback after the idle delay. Release blocker, to C for May.
