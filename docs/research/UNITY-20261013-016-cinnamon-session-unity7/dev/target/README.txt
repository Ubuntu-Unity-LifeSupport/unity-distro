cinnamon-session 6.4.2-1+unity7 (dev build of 954e756: UNITY-20261013-016, -020, -022) with
unity-settings-daemon +unity16 and light-locker +unity4 (dev builds): target run, 2026-10-13. Times EEST.

Setup (01-install.txt): target-desktop restored from Published-stack-2026-10-08 and updated from the live
repository (cinnamon-session +unity6, u-s-d +unity15, light-locker +unity3); the six debs of the three dev
builds installed with apt (u-s-d's Breaks: cinnamon-session (<< 6.4.2-1+unity7) satisfied, no force);
cold boot. Running binaries are the new ones (02-boot.txt; the "(deleted)" mappings of u-s-d are
pulseaudio memfds and a SysV shared memory segment).

UNITY-20261013-016 (idle delay from the Control Center):
- org.gnome.desktop.session idle-delay 60, org.cinnamon.desktop.session idle-delay 600, last input
  17:50:16: at t+80 s presence idle, IdleHint yes, LockedHint yes (03-gnome60.txt; which locker locked was
  not recorded). The presence follows the gnome key (with +unity6 it followed the cinnamon key: UNITY-20261008-023 dev/target-change1).
- The gnome key set to 0 while running: no idle after 150 s without input (04-gnome0-live.txt).
- A new cinnamon-session start (systemctl --user restart unity-session.service) sends exactly one
  AddIdleWatch to org.cinnamon.Muffin.IdleMonitor, with the gnome key's 300000 ms (06-session-restart.txt,
  restart-monitor.log; the other AddIdleWatch in the log, from :1.231 at 17:55:16, is not mapped to a
  process in the raw files).
- Keys reset afterwards (300 / 900).
Method note: a first attempt restarted LightDM (05-relogin.txt) and checked before the new session had
replaced the old process, so it counted a live re-add instead - not used. The next restart of
unity-session.service overlapped with the session LightDM was still starting and its stop timed out after
90 s (stop-journal.txt); a restart of unity-session.service on a settled session stopped and started at
once (07-session-restart-settled.txt).

UNITY-20261013-020 and -022: records in docs/research/UNITY-20261013-020-block-weak/ and
docs/research/UNITY-20261013-022-dbus-oom/.
