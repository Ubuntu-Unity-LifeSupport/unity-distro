#!/bin/sh
# One xterm per viewport of a 2x2 grid, plus a gnome-terminal on (1280,0).
. ~/envt.sh
for vp in "0 0" "1280 0" "0 800" "1280 800"; do
  set -- $vp
  xdotool set_desktop_viewport $1 $2; sleep 1.5
  setsid xterm -T "vp-$1-$2" -geometry 60x10+200+200 </dev/null >/dev/null 2>&1 &
  sleep 2
done
xdotool set_desktop_viewport 1280 0; sleep 1.5
setsid gnome-terminal --title=gt-1280-0 </dev/null >/dev/null 2>&1 &
sleep 3
xdotool set_desktop_viewport 0 0; sleep 1.5
