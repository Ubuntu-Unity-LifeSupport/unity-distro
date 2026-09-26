#!/bin/bash
# epi.sh LIB [shot] - epiphany with LD_PRELOAD=LIB, open its main menu with F10, click Passwords
lib=$1
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
pkill -9 -x epiphany; sleep 1; ulimit -c unlimited
env -i "${envs[@]}" LD_PRELOAD=$lib ${EXTRA} epiphany > /tmp/epi.out 2>&1 & p=$!
sleep 12
w=$(xdotool search --onlyvisible --pid $p | tail -1)
xdotool windowactivate --sync $w; xdotool key Escape; sleep 1
xdotool mousemove 1065 85 sleep 1 click 1 sleep 2
if [ "$2" = shot ]; then gnome-screenshot -f /tmp/epi-menu.png 2>/dev/null; kill -9 $p; exit; fi
xdotool mousemove $PX $PY sleep 1 click 1
sleep 5
alive=$(kill -0 $p 2>/dev/null && echo alive || echo DEAD)
echo "$(basename $lib .so): $alive, criticals $(grep -c 'assertion' /tmp/epi.out), passwords window $(xdotool search --onlyvisible --name '^Пароли$' 2>/dev/null | wc -l), nocsd-loaded $(grep -c 'libs/' /proc/$p/maps 2>/dev/null)"
for x in $(xdotool search --onlyvisible --pid $p 2>/dev/null); do echo "  window: $(xdotool getwindowname $x)"; done; kill -9 $p 2>/dev/null
