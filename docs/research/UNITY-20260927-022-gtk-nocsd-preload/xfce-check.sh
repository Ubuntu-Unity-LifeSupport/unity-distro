#!/bin/bash
# xfce-check.sh - in the running Xfce session: start mousepad (GTK3) with the
# session environment and with LD_PRELOAD removed, and compare client-side
# decoration properties; start gnome-text-editor (GTK4) with the session
# environment and take a screenshot.
export DISPLAY=:0
P=$(pidof -s xfwm4)
run() { # name cmd extra-env-filter
  tr '\0' '\n' < /proc/$P/environ | grep -v "$3" | tr '\n' '\0' > ~/.xc-env
  xargs -0 -a ~/.xc-env sh -c "exec env -i \"\$@\" setsid $2" _ > ~/xc-$1.log 2>&1 < /dev/null &
  sleep 8
}
props() { w=$(xdotool search --onlyvisible --class "$1" | tail -1); echo "$2 win=$w $(xprop -id "$w" _GTK_FRAME_EXTENTS _MOTIF_WM_HINTS 2>&1 | tr '\n' ' ')"; }
run mp-session mousepad '^$'; props mousepad "mousepad(session env): pid=$(pidof -s mousepad) maps_nocsd=$(grep -c libgtk-nocsd /proc/$(pidof -s mousepad)/maps)"
pkill -x mousepad; sleep 2
run mp-nopreload mousepad '^LD_PRELOAD='; props mousepad "mousepad(no LD_PRELOAD): pid=$(pidof -s mousepad) maps_nocsd=$(grep -c libgtk-nocsd /proc/$(pidof -s mousepad)/maps)"
pkill -x mousepad; sleep 2
run gte gnome-text-editor '^$'; G=$(pidof -s gnome-text-editor); echo "gnome-text-editor: maps_gtk4menu=$(grep -c libunity-gtk4-menu /proc/$G/maps) maps_nocsd=$(grep -c libgtk-nocsd /proc/$G/maps)"
gnome-screenshot -f ~/xfce-gte.png 2>/dev/null || xfce4-screenshooter -f -s ~/xfce-gte.png
pkill -x gnome-text-edit
