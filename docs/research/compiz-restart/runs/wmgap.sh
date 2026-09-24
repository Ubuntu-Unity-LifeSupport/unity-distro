#!/bin/sh
# Kill compiz with SIGNAL and report, every 0.5 s for 90 s, which compiz
# processes exist and whether a window manager owns the screen.
. ~/envt.sh
SIG=${1:-SEGV}
old=$(pgrep -x compiz); t0=$(date +%s.%N)
echo "old compiz=$old; helpers: $(pgrep -f '[l]ibgtk-nocsd.so.0 /usr/bin/compiz' | tr '\n' ' ')"
kill -$SIG $old
last=""
for i in $(seq 1 180); do
  now=$(date +%s.%N); dt=$(echo "$now - $t0" | bc | cut -c1-5)
  pids=$(pgrep -x compiz | tr '\n' ' ')
  wm=$(xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -q "window id" && echo wm || echo none)
  st="compiz=[$pids] $wm $(systemctl --user is-active unity7.service)"
  [ "$st" != "$last" ] && echo "t=+${dt}s $st"
  last=$st
  sleep 0.5
done
journalctl --since "-95s" --no-pager -o short-iso | grep -E "GTK-NoCSD|unity7.service|segfault|general protection" | tail -12
