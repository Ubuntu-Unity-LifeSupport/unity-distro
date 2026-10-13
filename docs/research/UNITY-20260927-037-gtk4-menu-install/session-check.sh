#!/bin/sh
# UNITY-20260927-037 target check (target2, after after.sh and a reboot into
# the Unity session): is libunity-gtk4-menu.so.0 in the session and in a GTK4
# application, and does the application export its menu?
# Usage (on target2, as mike): sh session-check.sh > log
set -u
export DISPLAY=:0
uid=$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus
echo "== session host=$(hostname) boot=$(cat /proc/sys/kernel/random/boot_id) utc=$(date -u +%FT%TZ)"
cpid=$(pgrep -u "$uid" -x compiz | head -1)
echo "== compiz pid=$cpid: $(tr '\0' '\n' < /proc/$cpid/environ | grep -E '^(XDG_CURRENT_DESKTOP|LD_PRELOAD)=' | tr '\n' ' ')"
echo "== systemd user manager LD_PRELOAD"; systemctl --user show-environment | grep ^LD_PRELOAD
app=file-roller
command -v $app >/dev/null || app=transmission-gtk
echo "== starting GTK4 application: $app"
systemd-run --user --collect --unit=check037 $app >/dev/null 2>&1
sleep 6
pid=$(systemctl --user show -p MainPID --value check037)
echo "pid=$pid"
echo "== LD_PRELOAD in its environment"; tr '\0' '\n' < /proc/$pid/environ | grep ^LD_PRELOAD
echo "== preload libraries mapped"; grep -o -E 'lib(unity-gtk4-menu|gtk-nocsd)[^ ]*' /proc/$pid/maps | sort -u
echo "== window properties (_GTK_MENUBAR_OBJECT_PATH is set when the menu is exported)"
for w in $(xprop -root _NET_CLIENT_LIST | sed 's/.*# //; s/,/ /g'); do
    if xprop -id "$w" _NET_WM_PID 2>/dev/null | grep -q " $pid\$"; then
        xprop -id "$w" WM_NAME _GTK_UNIQUE_BUS_NAME _GTK_MENUBAR_OBJECT_PATH _GTK_APPLICATION_OBJECT_PATH 2>/dev/null
    fi
done
systemctl --user stop check037 2>/dev/null
echo "== done"
