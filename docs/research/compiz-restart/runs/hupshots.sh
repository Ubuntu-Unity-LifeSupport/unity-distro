#!/bin/sh
# SIGHUP compiz, wait, then screenshot each viewport of the 2x2 grid.
. ~/envt.sh
xdotool set_desktop_viewport 0 0; sleep 1
killall -1 compiz; sleep ${1:-30}
for vp in "0 0" "1280 0" "0 800" "1280 800"; do
  set -- $vp
  xdotool set_desktop_viewport $1 $2; sleep 2
  gnome-screenshot -f /tmp/vp-$1-$2.png 2>/dev/null
done
xdotool set_desktop_viewport 0 0
