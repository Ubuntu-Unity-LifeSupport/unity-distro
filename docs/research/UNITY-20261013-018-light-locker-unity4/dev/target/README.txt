UNITY-20261013-018: target run of light-locker 1.8.0-3ubuntu4+unity4 (dev build of 66e1974, not the gate build)
with unity-settings-daemon +unity16 (dev build, UNITY-20261008-023), 2026-10-13. Times EEST on the target.

Setup (01-install.txt): target-desktop restored from Published-stack-2026-10-08 and updated from the live
repository earlier the same day (cinnamon-session 6.4.2-1+unity5, light-locker +unity3, u-s-d +unity15);
the u-s-d +unity16 debs and light-locker_1.8.0-3ubuntu4+unity4_amd64.deb (sha256 e493b6aa...) installed
with dpkg -i --force-breaks (u-s-d +unity16's Breaks on cinnamon-session << 6.4.2-1+unity7); cold boot.
Without UNITY-20261013-016, cinnamon-session takes its delay from org.cinnamon.desktop.session idle-delay:
set to 60 for the runs, reset to 900 afterwards. The running light-locker is the installed binary
(exe sha256 7cce20ba...). dbus-monitor recorded Inhibit/UnInhibit/Uninhibit (monitor-inhibit.log).
xdotool is not in the snapshot and its installation did not happen (apt), so the runs give no synthetic
input; the idle times printed show when input was last seen. (03-run1-close.txt starts with the
line "xdotool installed for the observation", printed by the script after the apt call whether or not it
installed; 05 shows that it was not.)

Run 1 (02-04): VLC 3.0.23 playing a video in a loop. VLC's org.freedesktop.ScreenSaver.Inhibit ("vlc",
"Воспроизведение мультимедиа.") was followed by light-locker's org.gnome.SessionManager.Inhibit with the
same strings, xid 0; cinnamon-session lists Inhibitor1 (app vlc, flags 8), IsInhibited(8) true. After
113 s without input (delay 60 s) presence available, IdleHint no, not locked (screenshot 02).
VLC closed normally: its UnInhibit was followed by light-locker's Uninhibit to the session manager's
unique name (:1.51); no inhibitor left. About 85 s later, with no inhibitor: presence idle, IdleHint
yes, LockedHint yes (which locker locked was not recorded) - normal idle blank+lock unchanged.
Run 2 (05): VLC playing (Inhibitor2), kill -9 VLC: inhibitor gone within 3 s.
Run 3 (05): light-locker-command -i held: Inhibitor3 (app "Unknown", flags 8); kill -9 of it: gone.
Run 4 (06): a one-shot dbus-send Inhibit (the caller exits at once): no inhibitor left - intended.
Run 5 (06): VLC playing (Inhibitor5) and loginctl lock-session: the session locks (LockedHint yes,
light-locker active) - manual locking is not held off by the forwarded inhibitor.
Run 6 (06, 07): snap Firefox 149 playing a local video: Inhibitor6 (app firefox_firefox, reason
"Воспроизведение звука", flags 8) 7 s after the start; gone after Firefox was closed. (The first check in
06 came too early and saw none.)
Every application Inhibit gave exactly one session-manager inhibitor; u-s-d (queued for the name) did not
add any.

Not measured here: idle sleep held off by the flag-8 inhibitor (sleep-inactive is 0 on this machine and
u-s-d's power plugin skips idle actions in a VM).

Result: PASS.
