#!/bin/sh
# Put xterm W on the bottom-left viewport, then sample its client and frame
# position through a SIGHUP restart of compiz.
. ~/envt.sh
W=${1:-0x3a00020}
xdotool set_desktop_viewport 0 0; sleep 1
xdotool windowmove $W 200 1000; sleep 2
pos() { echo "$(xwininfo -id $W | awk '/Absolute upper-left Y/{print $4}') ext=$(xprop -id $W _NET_FRAME_EXTENTS 2>/dev/null | sed 's/.*= //')"; }
echo "before: y=$(pos)"
killall -1 compiz
last=""
for i in $(seq 1 80); do
  p=$(pos); [ "$p" != "$last" ] && echo "t=+$((i/2)).$((i%2*5))s y=$p"; last=$p; sleep 0.5
done
echo "after: y=$(pos)"
