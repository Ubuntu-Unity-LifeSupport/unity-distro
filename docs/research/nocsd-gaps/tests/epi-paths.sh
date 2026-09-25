#!/bin/bash
# epi-paths.sh MODE - MODE own: click Passwords in epiphany's own menu; MODE global: activate the stand-in over D-Bus
mode=$1
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
pkill -9 -x epiphany; sleep 2
env -i "${envs[@]}" epiphany > /tmp/epi-$mode.out 2>&1 & p=$!
sleep 18
w=$(xdotool search --onlyvisible --pid $p | tail -1)
xdotool windowactivate --sync $w; xdotool key Escape; sleep 1
if [ $mode = own ]; then
	xdotool mousemove 1065 85 sleep 1 click 1 sleep 2 mousemove 950 361 sleep 1 click 1
else
	bus=$(xprop -id $w _GTK_UNIQUE_BUS_NAME | sed -n 's/.*= "\(.*\)"/\1/p')
	wp=$(xprop -id $w _GTK_WINDOW_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
	timeout 8 gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Activate gtk-nocsd-win-passwords '[]' '{}' >/dev/null 2>&1
fi
sleep 5
alive=$(kill -0 $p 2>/dev/null && echo alive || echo DEAD)
echo "$mode: $alive, criticals $(grep -c 'preferred_size: assertion' /tmp/epi-$mode.out), passwords window $(xdotool search --onlyvisible --name '^Пароли$' 2>/dev/null | wc -l)"
kill -9 $p 2>/dev/null
