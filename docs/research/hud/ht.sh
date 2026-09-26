#!/bin/bash
# ht.sh NAME "command" windowclass "query"
# Starts the application in the session environment (taken from compiz),
# opens the HUD over it with a tap of Alt, types the query, takes a screenshot.
export DISPLAY=:0
n=$1 cmd=$2 cls=$3 q=$4
if ! xdotool search --onlyvisible --class "$cls" >/dev/null 2>&1; then
  P=$(pgrep -x compiz)
  (cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "$cmd") > ~/.ht-args
  xargs -0 -a ~/.ht-args env -i > ~/app-$n.log 2>&1 < /dev/null &
  i=0; while ! xdotool search --onlyvisible --class "$cls" >/dev/null 2>&1 && [ $i -lt 90 ]; do sleep 1; i=$((i+1)); done
  sleep 12
fi
w=$(xdotool search --onlyvisible --class "$cls" | tail -1)
xdotool windowactivate --sync "$w"; sleep 1
xdotool key Alt_L; sleep 3
xdotool type --delay 300 "$q"; sleep 6
gnome-screenshot -f ~/hud-$n.png 2>/dev/null
xdotool key Escape; sleep 1
echo "$n: win=$w active=$(xdotool getactivewindow getwindowname) hud=$(pgrep -x hud-service)"
