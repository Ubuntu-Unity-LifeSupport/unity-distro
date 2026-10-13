#!/bin/sh
# Verifier UNITY-20260928-022: Keyboard/Screen calls in flight while the
# plugin is switched on and off (no gdb): does every call get an answer,
# does the daemon survive the start() window before the kbd proxy is ready?
. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.power
P=$(pgrep -x unity-settings-); T=$(date '+%F %T')
echo "## start $T pid $P"
for M in org.gnome.SettingsDaemon.Power.Keyboard.StepUp org.gnome.SettingsDaemon.Power.Screen.GetPercentage; do
  echo "== $M: 20 calls in flight for 20 s while toggling active 15x"
  python3 /tmp/kbdrace.py 20 20 $M &
  R=$!
  sleep 1
  for i in $(seq 1 15); do gsettings set $S active false; sleep 0.4; gsettings set $S active true; sleep 0.6; done
  wait $R
  echo "  u-s-d pid now: $(pgrep -x unity-settings-) (was $P); NRestarts $(systemctl --user show -p NRestarts --value unity-settings-daemon)"
done
echo "== journal since $T"
journalctl --user -u unity-settings-daemon --since "$T" --no-pager | grep -iE "abort|assert|segfault|dumped|critical|signal|core" | cut -c1-220 | sort | uniq -c | head
journalctl --since "$T" --no-pager | grep -iE "unity-settings.*(segfault|dumped|SIGSEGV|SIGABRT)|systemd-coredump" | cut -c1-220 | head
echo "  crash files: $(ls /var/crash | grep -c unity-settings)"
echo "  active: $(gsettings get $S active)"

