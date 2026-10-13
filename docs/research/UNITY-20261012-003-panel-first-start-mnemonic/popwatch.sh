#!/bin/bash
# popwatch.sh SECONDS - on target2: every 50 ms for SECONDS, the number of visible windows of unity-panel-service
# (its menu popups) and the active window; one timestamped line per change. Started just before a key from the host,
# it gives the time from the key (ShowEntry in the monitor) to the popup being mapped.
set -u
export $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep -E '^XAUTHORITY=') DISPLAY=:0
ps=$(pgrep -x unity-panel-ser)
end=$(( $(date +%s) + $1 )); last=
while [ "$(date +%s)" -lt "$end" ]; do
  n=$(xdotool search --onlyvisible --pid "$ps" 2>/dev/null | wc -l); a=$(xdotool getactivewindow 2>/dev/null)
  cur="panel-service visible windows $n, active $a"
  [ "$cur" != "$last" ] && echo "$(date -u +%T.%N | cut -c1-12) $cur"; last=$cur
  sleep 0.05
done
