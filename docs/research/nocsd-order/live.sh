#!/bin/bash
# usage: live.sh <name> <cmd...> - run in the live Unity session's environment
# (its own LD_PRELOAD, unchanged), then report menubar, mapped libs, panel shot
name=$1; shift
pid=$(pgrep -x compiz | head -1)
mapfile -d '' envs < /proc/$pid/environ
log=$HOME/b/live/$name.log; mkdir -p $HOME/b/live; rm -f $log
env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=$log "$@" >$HOME/b/live/$name.out 2>&1 &
app=$!; sleep 8
export $(tr '\0' '\n' < /proc/$pid/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
apid=$(sed -n "1s/^\\[unity-gtk4-menu \\([0-9]*\\)\\].*/\\1/p" $log); [ -z "$apid" ] && apid=$app; alive=$(kill -0 $apid 2>/dev/null && echo yes || echo NO)
echo "== $name: pid $apid alive=$alive LD_PRELOAD=$(tr '\0' '\n' </proc/$apid/environ | sed -n 's/^LD_PRELOAD=//p')"
grep -oE '/usr/lib/x86_64-linux-gnu/lib(unity-gtk4-menu|gtk-nocsd)\.so\.0' /proc/$apid/maps | sort -u
dpkg-query -W -f='${Version}\n' libunity-gtk4-menu0
w=$(xdotool search --pid $apid --onlyvisible 2>/dev/null | tail -1)
xprop -id $w _GTK_UNIQUE_BUS_NAME _GTK_MENUBAR_OBJECT_PATH _GTK_APPLICATION_OBJECT_PATH WM_NAME 2>/dev/null
bus=$(xprop -id $w _GTK_UNIQUE_BUS_NAME | sed -n 's/.*= "\(.*\)"/\1/p')
mb=$(xprop -id $w _GTK_MENUBAR_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
[ -n "$mb" ] && gdbus call --session -d "$bus" -o "$mb" -m org.gtk.Menus.Start '[0,1,2]' | grep -oE "'label': <'[^']*'>" | head -12 | tr '\n' ' '; echo
echo "-- shim log:"; grep -E 'hooked|export|through|our own' $log 2>/dev/null | head -5
xdotool windowactivate --sync $w 2>/dev/null; sleep 1
import -window root -crop 1280x60+0+0 $HOME/b/live/$name-panel.png
# open the first global menu entry (Unity shows the menu when the pointer is on the panel)
xdotool mousemove 90 12 sleep 1 click 1; sleep 2
import -window root $HOME/b/live/$name-menu.png
xdotool key Escape
kill $apid 2>/dev/null; sleep 1
