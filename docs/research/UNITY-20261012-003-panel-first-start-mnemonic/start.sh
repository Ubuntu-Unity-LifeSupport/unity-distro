#!/bin/bash
# start.sh TAG APP [ARGS...] - on target2 in the Unity session (as mike over ssh), the user's view of the live
# stack: start APP in the session's environment taken from compiz (its own LD_PRELOAD left as it is), focus its
# window, print the exported menu (audit.py) and the window's _GTK_* properties. Before the start, a dbus-monitor
# on the session bus records every org.gtk.Menus and org.gtk.Actions call into /tmp/mon-TAG.txt, so it is visible
# whether and when the panel subscribes to the menu; it keeps running until stop.sh TAG. Keys and screenshots then
# come from the host (vbox send_keys / screenshot). NOAUDIT=1 skips audit.py, which is itself an org.gtk.Menus
# subscriber, so the panel is the only one.
set -u
B=~/b1203
tag=$1; app=$2; shift 2
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
for a in gnome-text-edit gnome-calculator nautilus loupe baobab gnome-clocks; do pkill -x $a; done; sleep 1
dbus-monitor --session "interface='org.gtk.Menus'" "interface='org.gtk.Actions'" "interface='com.canonical.Unity.Panel.Service'" > /tmp/mon-$tag.txt 2>&1 &
echo $! > /tmp/mon-$tag.pid
# the root window's _NET_ACTIVE_WINDOW, one timestamped line per change, until stop.sh TAG
xprop -root -spy _NET_ACTIVE_WINDOW 2>/dev/null | while read -r l; do echo "$(date -u +%T.%N | cut -c1-12) $l"; done > /tmp/act-$tag.txt 2>&1 &
echo $! > /tmp/act-$tag.pid; sleep 1
echo "$tag start $(date -u +%T.%N | cut -c1-12)Z, boot $(uptime -s), session up since $(ps -o lstart= -p $sp)"
env -i "${envs[@]}" $app "$@" > /tmp/s-$tag.out 2>&1 & p=$!
w=
for i in $(seq 40); do w=$(xdotool search --onlyvisible --pid $p 2>/dev/null | tail -1); [ -n "$w" ] && break; sleep 0.25; done
echo "  window $w mapped at $(date -u +%T.%N | cut -c1-12)Z"
sleep 4
[ -n "$w" ] && xdotool windowactivate --sync $w; sleep 1
echo "  $app pid $p window $w ($(xdotool getwindowname $w 2>/dev/null)) active $(xdotool getactivewindow)"
echo "  preload in the process: $(tr '\0' '\n' < /proc/$p/environ | grep '^LD_PRELOAD=')"
echo "  libraries mapped: $(grep -oE 'lib(gtk-nocsd|unity-gtk4-menu)\.so\.0' /proc/$p/maps | sort -u | xargs)"
xprop -id "$w" | grep '^_GTK_' | sed 's/^/  /'
if [ -z "${NOAUDIT:-}" ]; then python3 $B/audit.py $p > /tmp/audit-$tag.out 2>&1; else echo "  NOAUDIT: menu not read" > /tmp/audit-$tag.out; fi
grep -E "^ *(ok|disabled|MISSING|-|NO-)" /tmp/audit-$tag.out | sed 's/  */ /g' | head -16 | sed 's/^/  /'
echo "  menu labels: $(grep -cE '^ *(ok|disabled|MISSING)' /tmp/audit-$tag.out), with an underscore in the label:" \
     "$(grep -E '^ *(ok|disabled|MISSING|-)' /tmp/audit-$tag.out | awk '{$1=""; $2=""; print}' | grep -c '_')"
echo "  ready $(date -u +%T.%N | cut -c1-12)Z"
