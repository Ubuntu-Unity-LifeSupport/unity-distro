#!/bin/bash
# UNITY-20260927-052 (agent A): do the daemon's own watches still work after
# D-Bus clients left? Needs the --debug wrapper (usd-debug-wrapper-install.sh,
# from UNITY-20260927-005). Restart the daemon: its cursor plugin hides the
# pointer and arms a user-active watch. Two clients add a watch and leave.
# Then real mouse input: the plugin must log "Attempting to show the cursor".
. ~/envt.sh
N=$(grep -l "ImExPS/2" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5)
systemctl --user restart unity-settings-daemon.service
for i in $(seq 1 30); do P=$(pgrep -x unity-settings- | head -1); [ -n "$P" ] && grep -q "Attempting to hide" /tmp/usd-$P.log 2>/dev/null && break; sleep 1; done
sleep 2; echo "u-s-d $(dpkg-query -W -f '${Version}' unity-settings-daemon), pid $P, hidden: $(grep -c 'Attempting to hide' /tmp/usd-$P.log)"
python3 ~/watch-client.py active; python3 ~/watch-client.py active; sleep 3
echo "after two departures: pid $(pgrep -x unity-settings-)"
n=$(wc -l < /tmp/usd-$P.log)
sudo ~/evinject.py /dev/input/$N 8 4 2 >/dev/null; sleep 2
after=$(tail -n +$((n + 1)) /tmp/usd-$P.log | grep -oE 'Attempting to (hide|show) the cursor|became active|double free[^:]*' | tr '\n' ';')
r=FAIL; echo "$after" | grep -q "Attempting to show" && [ -d /proc/$P ] && r=PASS
echo "after the input, pid $P logged: ${after:-nothing} => $r"
