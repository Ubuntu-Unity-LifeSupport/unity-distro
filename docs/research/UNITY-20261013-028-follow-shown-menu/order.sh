#!/bin/bash
# order.sh - T4 on target2 (as mike over ssh): research/nocsd-order/order-0.9.sh's run against the installed
# unity-gtk4-menu, with the packaged gtk-nocsd only (no build of gtk-nocsd's own on a Clean-2 machine): each program
# under Xvfb for 7 s in three orders - ours alone, ours:gtk-nocsd, gtk-nocsd:ours. rc=124 is alive at the timeout;
# "menu-lines" counts the library's hooked/exported/registered lines, as order-0.9.sh does. classtest and gjstest come
# from the package's tests/ (built on target2), gjstest is run with gjs -m.
set -u
B=~/b028t
Xvfb :77 -screen 0 1280x800x24 > /dev/null 2>&1 & XV=$!; sleep 2
export DISPLAY=:77 XDG_CURRENT_DESKTOP=Unity UNITY_GTK4_MENU_DEBUG=1
eval $(dbus-launch --sh-syntax)
M=/usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0; N=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
echo "== order at $(date -u +%FT%TZ); $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}, ' libunity-gtk4-menu0)$(dpkg-query -W -f='libgtk-nocsd0 ${Version}' libgtk-nocsd0)"
tot=0; alive=0
for a in "$B/classtest" "gjs -m $B/gjstest.js" gnome-text-editor gnome-characters gnome-calculator nautilus gnome-clocks \
         gnome-contacts gnome-font-viewer gnome-weather; do
  for ord in "$M" "$M:$N" "$N:$M"; do
    LD_PRELOAD=$ord timeout -s TERM 7 $a > /tmp/ord.out 2>&1; rc=$?; tot=$((tot + 1))
    h=$(grep -ciE 'hooked|exported|registered' /tmp/ord.out)
    [ $rc = 124 ] && alive=$((alive + 1))
    printf '  %-20s %-14s rc=%-3s menu-lines=%s\n' "$(basename "${a##* }")" \
      "$(echo "$ord" | sed "s#$M#ours#; s#$N#nocsd#")" "$rc" "$h"
  done
done
echo "== $alive of $tot alive at the timeout"
kill $XV $DBUS_SESSION_BUS_PID
