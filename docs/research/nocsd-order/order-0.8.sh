#!/bin/bash
# issue #1: nocsd head -O0 (N0) and archive 4.8 -O2 (N), both orders
Xvfb :77 -screen 0 1280x800x24 >/dev/null 2>&1 & XV=$!; sleep 2
export DISPLAY=:77 XDG_CURRENT_DESKTOP=Unity
eval $(dbus-launch --sh-syntax)
N0=$HOME/b/nocsd-head/libgtk-nocsd.so.0; N=libgtk-nocsd.so.0; M=libunity-gtk4-menu.so.0
for a in gnome-text-editor gnome-characters gnome-calculator nautilus gnome-clocks gedit; do command -v $a >/dev/null || continue
  for ord in "$N0" "$M:$N0" "$N0:$M" "$M:$N" "$N:$M"; do
    LD_PRELOAD=$ord timeout -s TERM 6 $a >/tmp/ord.out 2>&1; rc=$?
    printf '%-18s %-62s rc=%s\n' "$a" "${ord//$HOME\/b\//}" "$rc"
  done
done
kill $XV $DBUS_SESSION_BUS_PID
