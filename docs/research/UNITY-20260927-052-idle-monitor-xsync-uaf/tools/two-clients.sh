#!/bin/bash
# UNITY-20260927-052 (agent A): one run of the reproducer - two IdleMonitor
# clients each add a user-active watch and exit without RemoveWatch; report
# whether unity-settings-daemon survived (same PID) and what systemd logged.
. ~/envt.sh
P0=$(pgrep -x unity-settings-); t0=$(date '+%F %T')
python3 ~/watch-client.py active; sleep 2
python3 ~/watch-client.py active; sleep 25
P1=$(pgrep -x unity-settings-)
[ "$P0" = "$P1" ] && r="SURVIVED" || r="DIED"
echo "u-s-d $(dpkg-query -W -f '${Version}' unity-settings-daemon): pid $P0 -> $P1: $r"
journalctl --user --since "$t0" --no-pager -o short-precise | grep -E "double free|free\(\)|corruption|Main process exited|Scheduled restart" | sed 's/^/  /'
