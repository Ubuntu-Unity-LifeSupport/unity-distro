#!/bin/sh
# Print every client window with its absolute position on the large desktop.
. ~/envt.sh
vp=$(xprop -root _NET_DESKTOP_VIEWPORT | sed 's/.*= //;s/,//')
set -- $vp; vx=$1; vy=$2
echo "viewport=$vx,$vy geometry=$(xprop -root _NET_DESKTOP_GEOMETRY | sed 's/.*= //')"
# no window manager (compiz restarting): no list; xwininfo -id garbage would
# wait for a mouse click (UNITY-20260927-008)
xprop -root _NET_CLIENT_LIST | grep -q '#' || { echo "no _NET_CLIENT_LIST"; exit 0; }
for w in $(xprop -root _NET_CLIENT_LIST | sed 's/.*# //;s/,//g'); do
  name=$(xprop -id $w _NET_WM_NAME 2>/dev/null | grep ' = ' | sed 's/.*= //')
  # xterm with allowTitleOps off sets only WM_NAME (UNITY-20260927-008)
  [ -n "$name" ] || name=$(xprop -id $w WM_NAME 2>/dev/null | grep ' = ' | sed 's/.*= //')
  x=$(xwininfo -id $w | awk '/Absolute upper-left X/{print $4}')
  y=$(xwininfo -id $w | awk '/Absolute upper-left Y/{print $4}')
  st=$(xprop -id $w _NET_WM_STATE 2>/dev/null | sed 's/.*= //')
  echo "$w abs=$((x+vx)),$((y+vy)) rel=$x,$y $name [$st]"
done
