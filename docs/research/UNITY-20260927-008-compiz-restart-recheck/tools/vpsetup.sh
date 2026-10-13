#!/bin/sh
# One xterm per viewport of a 2x2 grid, plus a gnome-terminal on (1280,0).
# (UNITY-20260927-008: titles pinned so that windows are found by name.)
. ~/envt.sh
for vp in "0 0" "1280 0" "0 800" "1280 800"; do
  set -- $vp
  xdotool set_desktop_viewport $1 $2; sleep 1.5
  setsid xterm -xrm "XTerm*allowTitleOps: false" -T "vp-$1-$2" -geometry 60x10+200+200 </dev/null >/dev/null 2>&1 &
  sleep 2
done
xdotool set_desktop_viewport 1280 0; sleep 1.5
# bash would retitle the window; sh keeps the title set here
setsid gnome-terminal -- sh -c 'printf "\033]0;gt-1280-0\007"; exec sh' </dev/null >/dev/null 2>&1 &
sleep 3
xdotool set_desktop_viewport 0 0; sleep 1.5
