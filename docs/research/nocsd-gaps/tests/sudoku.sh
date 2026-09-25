#!/bin/bash
export $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
p=$(cat /tmp/sud.pid); w=$(xdotool search --onlyvisible --pid $p | tail -1)
bus=$(xprop -id $w _GTK_UNIQUE_BUS_NAME | sed -n 's/.*= "\(.*\)"/\1/p')
wp=$(xprop -id $w _GTK_WINDOW_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
d() { gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Describe gtk-nocsd-game-view-reset-board 2>&1 | cut -c1-60; }
echo "start view:        $(d)"
xdotool windowactivate --sync $w; xdotool mousemove 389 543 sleep 1 click 1; sleep 3
echo "game started:      $(d)"
for k in 1 2 3 4 5 6 7 8 9; do xdotool key $k; done; sleep 1
xdotool key Right; for k in 1 2 3 4 5 6 7 8 9; do xdotool key $k; done; sleep 1
echo "after typing:      $(d)"
gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Activate gtk-nocsd-game-view-reset-board '[]' '{}' >/dev/null 2>&1; sleep 2
echo "after reset:       $(d)"
import -window root /tmp/sud2.png
