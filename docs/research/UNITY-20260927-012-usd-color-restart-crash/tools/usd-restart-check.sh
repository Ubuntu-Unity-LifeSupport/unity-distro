#!/bin/sh
# UNITY-20260927-012: after a restart through Unity's dialog - did
# unity-settings-daemon crash in the previous boot? apport's report (kept
# aside under /var/tmp/u012-crashes) and the journal. Prints one line.
J="journalctl -b -1 --no-pager"
c=$(ls /var/crash/_usr_lib_unity-settings-daemon_unity-settings-daemon.*.crash 2>/dev/null | wc -l)
if [ "$c" -gt 0 ]; then
  f=$(ls /var/crash/_usr_lib_unity-settings-daemon_unity-settings-daemon.*.crash | head -1)
  sig=$(sudo grep -a "^Signal:" "$f"); ts=$(sudo grep -a "^Date:" "$f")
  sudo mkdir -p /var/tmp/u012-crashes; sudo mv "$f" /var/tmp/u012-crashes/$(date +%s).crash
else sig=; ts=; fi
echo "boot $(uptime -s): u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) previous-boot clicked=$($J -t u009 | grep -c clicking) u-s-d crash reports=$c $sig $ts; journal u-s-d criticals=$($J | grep -c 'unity-settings-daemon.*\(CRITICAL\|assertion\)')"
# how u-s-d left (G_MESSAGES_DEBUG=all from the test drop-in)
$J -o short-precise | grep -E "unity-settings-daemon.*(Got Stop signal|Got a SessionOver|Received SIGTERM|Stopping settings manager|Shutting down|SettingsDaemon finished|Name taken or bus went away|Stopping power manager|Stopping color manager)" | cut -c1-170 | sed 's/^/    /' | head -10
