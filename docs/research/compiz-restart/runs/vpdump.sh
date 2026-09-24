#!/bin/sh
# Print every client window with its absolute position on the large desktop.
. ~/envt.sh
vp=$(xprop -root _NET_DESKTOP_VIEWPORT | sed 's/.*= //;s/,//')
set -- $vp; vx=$1; vy=$2
echo "viewport=$vx,$vy geometry=$(xprop -root _NET_DESKTOP_GEOMETRY | sed 's/.*= //')"
for w in $(xprop -root _NET_CLIENT_LIST | sed 's/.*# //;s/,//g'); do
  name=$(xprop -id $w _NET_WM_NAME 2>/dev/null | sed 's/.*= //')
  x=$(xwininfo -id $w | awk '/Absolute upper-left X/{print $4}')
  y=$(xwininfo -id $w | awk '/Absolute upper-left Y/{print $4}')
  st=$(xprop -id $w _NET_WM_STATE 2>/dev/null | sed 's/.*= //')
  echo "$w abs=$((x+vx)),$((y+vy)) rel=$x,$y $name [$st]"
done
