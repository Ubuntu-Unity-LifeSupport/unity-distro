#!/bin/bash
# kshot.sh NAME CLICKX [VAR=value ...] -- CMD...   (Plasma: widget in the bottom panel)
# CLICKX=0: only screenshot the panel with the window active
name=$1; cx=$2; shift 2
extra=(); while [ "$1" != "--" ]; do extra+=("$1"); shift; done; shift
sp=$(pgrep -x plasmashell | head -1)
mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
out=$HOME/b/live/$name; rm -f $out-*.png
env -i "${envs[@]}" "${extra[@]}" "$@" > $out.out 2>&1 & app=$!
sleep 8
w=$(xdotool search --onlyvisible --pid $app 2>/dev/null | tail -1)
[ -n "$w" ] && xdotool windowactivate --sync $w 2>/dev/null
sleep 3
import -window root $out-panel.png
if [ "$cx" != 0 ]; then xdotool mousemove $cx 769 sleep 1 click 1; sleep 2; import -window root $out-open.png; xdotool key Escape; fi
echo "$name: win ${w:-none} kde=$(xprop -id ${w:-0} _KDE_NET_WM_APPMENU_OBJECT_PATH 2>/dev/null | sed 's/.*= //')"
kill $app 2>/dev/null; sleep 1
