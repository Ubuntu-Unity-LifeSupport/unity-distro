#!/bin/bash
# dash.sh KEYS QUERY OUT - open a Dash lens with KEYS (xdotool key), type QUERY, screenshot to OUT
export DISPLAY=:0
xdotool key Escape; sleep 1
xdotool key $1; sleep 4
[ -n "$2" ] && xdotool type --delay 80 "$2"
sleep ${WAIT:-7}
gnome-screenshot -f "$3" 2>/dev/null
xdotool key Escape
