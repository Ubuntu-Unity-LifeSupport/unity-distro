#!/bin/sh
# UNITY-20260927-009: after a restart by tools/restart-via-dialog.sh - did
# compiz leave cleanly in the previous boot? Prints one line.
J="journalctl -b -1 --no-pager -o short-precise"
cores=$(ls /var/tmp/core.compiz.* 2>/dev/null | wc -l)
segv=$($J | grep -cE 'compiz\[[0-9]+\]: segfault|compiz.*general protection|Process [0-9]+ \(compiz\) of user [0-9]+ dumped core')
clicked=$($J -t u009 | grep -c "clicking")
echo "boot $(uptime -s): previous boot clicked=$clicked compiz cores in /var/tmp=$cores journal segv/dump=$segv last compiz line: $($J | grep -E ' compiz\[' | tail -1 | cut -c1-140)"
