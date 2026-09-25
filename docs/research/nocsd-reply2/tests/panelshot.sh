#!/bin/bash
# panelshot.sh NAME X Y [VAR=value ...] -- CMD...
# start CMD in the live session's environment (plus VARs), focus it, screenshot
# the screen, click the panel at X,Y (first global menu entry), screenshot again
name=$1; x=$2; y=$3; shift 3
extra=()
while [ "$1" != "--" ]; do extra+=("$1"); shift; done; shift
sp=$(pgrep -x ${SESSPROC:-compiz} | head -1)
mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
out=$HOME/b/live/$name; rm -f $out-*.png
env -i "${envs[@]}" "${extra[@]}" "$@" > $out.out 2>&1 & app=$!
sleep 7
w=$(xdotool search --onlyvisible --pid $app 2>/dev/null | tail -1)
[ -n "$w" ] && xdotool windowactivate --sync $w 2>/dev/null
sleep 2
import -window root -crop 1280x40+0+0 $out-panel.png
xdotool mousemove $x $y sleep 1 click 1; sleep 2
import -window root $out-open.png
xdotool key Escape
echo "$name: pid $app win ${w:-none} menubar=$(xprop -id ${w:-0} _GTK_MENUBAR_OBJECT_PATH 2>/dev/null | sed 's/.*= //') kde=$(xprop -id ${w:-0} _KDE_NET_WM_APPMENU_OBJECT_PATH 2>/dev/null | sed 's/.*= //')"
kill $app 2>/dev/null; sleep 1
