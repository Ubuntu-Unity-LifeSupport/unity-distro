#!/bin/bash
# start.sh VARIANT APP [ARGS...] - on target2 in the Unity session (as mike over ssh):
# install one gtk-nocsd build as /usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0, start APP in the session's
# environment (taken from compiz) with LD_PRELOAD=libgtk-nocsd.so.0 ONLY (our libunity-gtk4-menu, which the session
# also preloads, would export a second menu), focus its window, and print the exported menu (audit.py) with the
# number of labels carrying a mnemonic underscore. Keys and screenshots then come from the host (vbox).
#   VARIANT: b76f3fb | fd4b76a (with GTK_NOCSD_MENU=1) | pkg (our packaged 4.8-1+unity3, the session's own
#            LD_PRELOAD left as it is: the user's view)
#   APP:     pinta | gnome-text-editor | nautilus | ... | any command
set -u
B=~/b1012
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
v=$1; app=$2; shift 2
case $v in
  b76f3fb|fd4b76a) lib=$B/libgtk-nocsd-$v.so.0; extra="LD_PRELOAD=libgtk-nocsd.so.0 GTK_NOCSD_MENU=1" ;;
  # our series as upstream carries it (2d50fe9, = the S build of UNITY-20261008-001), with its own switch
  2d50fe9) lib=$B/libgtk-nocsd-$v.so.0; extra="LD_PRELOAD=libgtk-nocsd.so.0 GTK_NOCSD_GLOBAL_MENU=1" ;;
  pkg) lib=$B/libgtk-nocsd.so.0.pkg; extra="" ;;
  *) echo "unknown variant $v"; exit 2 ;;
esac
sudo -n cp "$lib" $T.new && sudo -n mv $T.new $T
echo "installed $v: $(sha256sum < $T | cut -c1-16)"
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
for a in Pinta gnome-text-edit nautilus fractal loupe gnome-calculator baobab gnome-clocks titletest; do pkill -x $a; done; sleep 1
case $app in
  pinta) env -i "${envs[@]}" $extra DOTNET_ROLL_FORWARD=Major $B/Pinta-3.1.2/build/bin/Pinta "$@" > /tmp/s.out 2>&1 & p=$!; sleep 15 ;;
  *) env -i "${envs[@]}" $extra $app "$@" > /tmp/s.out 2>&1 & p=$!; sleep 9 ;;
esac
w=$(xdotool search --onlyvisible --pid $p | tail -1)
[ -n "$w" ] && xdotool windowactivate --sync $w; sleep 1
echo "$v $app pid $p window $w ($(xdotool getwindowname $w 2>/dev/null)) active $(xdotool getactivewindow)"
echo "  preload in the process: $(tr '\0' '\n' < /proc/$p/environ | grep '^LD_PRELOAD=')"
echo "  libraries mapped: $(grep -oE 'lib(gtk-nocsd|unity-gtk4-menu)\.so\.0' /proc/$p/maps | sort -u | xargs)"
python3 $B/audit.py $p > /tmp/audit.out 2>&1
grep -E "^ *(ok|disabled|MISSING|-)" /tmp/audit.out | sed 's/  */ /g' | head -14 | sed 's/^/  /'
# the label is the third field onward (status, action, label); action names carry underscores of their own
echo "  menu labels: $(grep -cE '^ *(ok|disabled|MISSING)' /tmp/audit.out), with an underscore in the label:" \
     "$(grep -E '^ *(ok|disabled|MISSING)' /tmp/audit.out | awk '{$1=""; $2=""; print}' | grep -c '_')"
