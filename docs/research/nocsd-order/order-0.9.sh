#!/bin/bash
# issue #1: packaged 0.9 (M), nocsd head -O0 (N0) and 4.8 -O2 (N), both orders; classtest + gjstest too
Xvfb :77 -screen 0 1280x800x24 >/dev/null 2>&1 & XV=$!; sleep 2
export DISPLAY=:77 XDG_CURRENT_DESKTOP=Unity UNITY_GTK4_MENU_DEBUG=1
eval $(dbus-launch --sh-syntax)
N0=$HOME/b/nocsd-head/libgtk-nocsd.so.0; N=libgtk-nocsd.so.0; M=libunity-gtk4-menu.so.0
tot=0; bad=0
for a in "$HOME/b/classtest" "gjs $HOME/b/gjstest.js" gnome-text-editor gnome-characters gnome-calculator nautilus gnome-clocks gnome-contacts gnome-font-viewer gnome-weather; do
  for ord in "$M" "$M:$N0" "$N0:$M" "$M:$N" "$N:$M"; do
    LD_PRELOAD=$ord timeout -s TERM 7 $a >/tmp/ord.out 2>&1; rc=$?; tot=$((tot+1))
    h=$(grep -ciE 'hooked|exported|registered' /tmp/ord.out)
    [ $rc = 124 ] || bad=$((bad+1))
    printf '%-26s %-40s rc=%-3s menu-lines=%s\n' "$(basename "${a%% *}")${a#* }" "$(echo $ord | sed "s#$HOME/b/##g")" "$rc" "$h"
  done
done 2>/dev/null | sed "s#$HOME/b/##"
kill $XV $DBUS_SESSION_BUS_PID
