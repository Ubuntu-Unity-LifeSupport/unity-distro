#!/bin/bash
# run.sh TAG [menubar] - on target2 in the Unity session (as mike over ssh): start Pinta 3.1.2 in the session's
# environment (taken from compiz, its own LD_PRELOAD left as it is) with unity-gtk4-menu's debug log on
# (UNITY_GTK4_MENU_DEBUG=1, UNITY_GTK4_MENU_LOG=/tmp/ugm-TAG.log), then print: the library's log lines with the time
# each was first seen (polled every 50 ms from the start), the first time the window is mapped, its _GTK_*
# properties, the exported menu (audit.py) and the panel service's entries for the window (sync.sh).
#   menubar: set Pinta's own setting menubar-shown=true first (View > Show/Hide > Menu Bar), so that Pinta calls
#            app.Menubar itself and uses a plain Gtk.ApplicationWindow (MainWindow.cs:363-412, WindowShell.cs:58-63)
set -u
B=~/b1204
tag=$1; mode=${2:-default}
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
pkill -x Pinta; sleep 1
S=~/.config/Pinta/settings.xml
case $mode in
  menubar) python3 $B/pinta_setting.py "$S" menubar-shown True ;;
  *)       python3 $B/pinta_setting.py "$S" menubar-shown False ;;
esac
rm -f /tmp/ugm-$tag.log
echo "== $tag ($mode) start $(date -u +%T.%N | cut -c1-12)Z, boot $(uptime -s), $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0)"
env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=/tmp/ugm-$tag.log DOTNET_ROLL_FORWARD=Major \
  $B/Pinta-3.1.2/build/bin/Pinta > /tmp/pinta-$tag.out 2>&1 & p=$!
seen=0; w=; wt=
for i in $(seq 400); do
  if [ -f /tmp/ugm-$tag.log ]; then
    n=$(wc -l < /tmp/ugm-$tag.log)
    if [ "$n" -gt "$seen" ]; then
      tail -n +$((seen + 1)) /tmp/ugm-$tag.log | head -n $((n - seen)) | sed "s/^/  $(date -u +%T.%N | cut -c1-12) log: /"
      seen=$n
    fi
  fi
  if [ -z "$w" ]; then
    w=$(xdotool search --onlyvisible --pid $p 2>/dev/null | tail -1)
    [ -n "$w" ] && { wt=$(date -u +%T.%N | cut -c1-12); echo "  $wt window $w mapped"; }
  fi
  [ -n "$w" ] && [ "$i" -gt 300 ] && break
  sleep 0.05
done
sleep 2
[ -f /tmp/ugm-$tag.log ] && tail -n +$((seen + 1)) /tmp/ugm-$tag.log | sed 's/^/  later log: /'
echo "  Pinta pid $p window $w ($(xdotool getwindowname $w 2>/dev/null))"
echo "  preload in the process: $(tr '\0' '\n' < /proc/$p/environ | grep '^LD_PRELOAD=')"
echo "  libraries mapped: $(grep -oE 'lib(gtk-nocsd|unity-gtk4-menu)\.so\.0' /proc/$p/maps | sort -u | xargs)"
xprop -id "$w" | grep '^_GTK_' | sed 's/^/  /'
python3 $B/audit.py $p > /tmp/audit-$tag.out 2>&1
grep -E "^ *(ok|disabled|MISSING|-|NO-)" /tmp/audit-$tag.out | sed 's/  */ /g' | head -12 | sed 's/^/  /'
echo "  menu labels: $(grep -cE '^ *(ok|disabled|MISSING)' /tmp/audit-$tag.out)"
bash $B/sync.sh "$tag" | grep -E "^==|win=$w" | sed 's/^/  /'
