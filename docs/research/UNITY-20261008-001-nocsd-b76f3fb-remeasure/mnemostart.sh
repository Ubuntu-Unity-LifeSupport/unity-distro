#!/bin/bash
# mnemostart.sh S|U|PKG APP - for the Alt-mnemonic check with real keys (vbox send_keys): install the build as
# libgtk-nocsd.so.0, start APP (pinta | gnome-text-editor | nautilus) in the session environment with that
# build's switch, wait, focus its window, and print what the exported menu looks like (audit.py), so the
# screenshot after the keys can be read against it. Keys and screenshots are sent from the host.
set -u
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
case $1 in
  S) lib=~/b081/nocsd-60ec176/libgtk-nocsd.so.0; var=GTK_NOCSD_GLOBAL_MENU=1 ;;
  U) lib=~/b081/nocsd-b76f3fb/libgtk-nocsd.so.0; var=GTK_NOCSD_MENU=1 ;;
  PKG) lib=~/b081/libgtk-nocsd.so.0.pkg; var= ;;
esac
sudo -n cp "$lib" $T.new && sudo -n mv $T.new $T
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
for a in Pinta gnome-text-edit nautilus; do pkill -x $a; done; sleep 1
case $2 in
  pinta) env -i "${envs[@]}" $var DOTNET_ROLL_FORWARD=Major ~/b081/Pinta-3.1.2/build/bin/Pinta > /tmp/m.out 2>&1 & p=$!; sleep 14 ;;
  *) env -i "${envs[@]}" $var $2 > /tmp/m.out 2>&1 & p=$!; sleep 8 ;;
esac
w=$(xdotool search --onlyvisible --pid $p | tail -1)
xdotool windowactivate --sync $w; sleep 1
echo "$1 $2 pid $p window $w active $(xdotool getactivewindow)"
python3 ~/b/audit.py $p 2>&1 | grep -E "^ {0,12}(ok|disabled|-)" | sed 's/  */ /g' | head -12
