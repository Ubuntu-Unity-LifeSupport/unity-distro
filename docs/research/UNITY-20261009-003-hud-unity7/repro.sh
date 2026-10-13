#!/bin/bash
# repro.sh STEP - UNITY-20261009-003/-004/-005 on target2 (as mike over ssh, in the Unity session), hud +unity6.
#   004      gnome-terminal: the "Создать окно" item in its exported GMenu (action and target), the action's
#            parameter type (org.gtk.Actions.Describe), then a legacy HUD client (StartQuery + ExecuteQuery) runs
#            the item while dbus-monitor records every org.gtk.Actions call; terminal windows before and after
#   003key   a legacy StartQuery, then ExecuteQuery with a string key: is hud-service still the same process?
#   003nowin every window closed and the desktop focused, then StartQuery + ExecuteQuery(uint64 0)
#   005      a Qt 5 probe: QStandardPaths::locate(ApplicationsLocation, x.desktop) with a relative XDG_DATA_HOME,
#            from a working directory that holds applications/x.desktop
set -u
B=~/b0309
export DISPLAY=:0
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
HUD="--dest com.canonical.hud --object-path /com/canonical/hud"
hudpid() { pgrep -x hud-service | head -1; }
start() { (env -i "${envs[@]}" setsid sh -c "$1" > /dev/null 2>&1 < /dev/null &); }
case $1 in
004)
  pkill -x gnome-terminal-; sleep 1
  start gnome-terminal; sleep 6
  w=$(xdotool search --onlyvisible --name "mike@target2" | tail -1); xdotool windowactivate --sync $w; sleep 1
  bus=$(xprop -id $w _GTK_UNIQUE_BUS_NAME | sed -n 's/.*= "\(.*\)"/\1/p')
  mb=$(xprop -id $w _GTK_MENUBAR_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
  app=$(xprop -id $w _GTK_APPLICATION_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
  win=$(xprop -id $w _GTK_WINDOW_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
  echo "terminal window $w bus $bus menubar $mb app $app win $win"
  python3 $B/menuitems.py "$bus" "$mb" "$app" "$win" "Создать окно"
  echo "terminal windows before: $(xdotool search --onlyvisible --name 'mike@target2' | wc -l)"
  dbus-monitor --session "interface='org.gtk.Actions'" > /tmp/act.txt 2>&1 & mon=$!; sleep 1
  python3 $B/hudexec.py "Создать окно"
  sleep 4; kill $mon
  echo "terminal windows after: $(xdotool search --onlyvisible --name 'mike@target2' | wc -l)"
  echo "org.gtk.Actions calls seen: $(grep -c 'member=Activate' /tmp/act.txt)"
  grep -A6 "member=Activate" /tmp/act.txt | head -24
  echo "hud-service pid $(hudpid)" ;;
003key)
  p=$(hudpid)
  python3 $B/hudexec.py "Создать окно" --key-string
  sleep 2; echo "after the string key: hud-service $(hudpid)"
  python3 $B/hudexec.py "Создать окно" --key-struct
  sleep 3; echo "hud-service before $p, after $(hudpid)"
  journalctl --user --since "-30 s" --no-pager | grep -iE "hud-service|sendErrorReply|QDBus" | tail -5 ;;
003nowin)
  for a in gnome-terminal- nautilus gnome-text-edit soffice.bin; do pkill -x $a; done; sleep 2
  xdotool key super+d 2>/dev/null; sleep 1
  echo "visible app windows: $(xdotool search --onlyvisible --class '.' 2>/dev/null | while read x; do xprop -id $x _GTK_UNIQUE_BUS_NAME 2>/dev/null; done | grep -c '=')"
  echo "active window: $(xdotool getactivewindow 2>&1) $(xdotool getwindowname $(xdotool getactivewindow) 2>&1)"
  p=$(hudpid)
  python3 $B/hudexec.py "" --key-zero
  sleep 3; echo "hud-service before $p, after $(hudpid)"
  coredumpctl --no-pager list hud-service 2>/dev/null | tail -2
  journalctl --user --since "-30 s" --no-pager | grep -iE "hud-service" | tail -5 ;;
005)
  g++ -fPIC -o $B/qpaths $B/qpaths.cpp $(pkg-config --cflags --libs Qt5Core) > $B/qpaths-build.log 2>&1; echo "qpaths build rc=$?"
  T=$(mktemp -d); mkdir -p $T/rel/applications $T/sys/applications
  printf '[Desktop Entry]\nType=Application\nName=X\n' > $T/rel/applications/x.desktop
  cd $T
  echo "cwd $T, ./rel/applications/x.desktop exists, XDG_DATA_DIRS=$T/sys (no x.desktop there)"
  env -i HOME=$HOME XDG_DATA_HOME=rel XDG_DATA_DIRS=$T/sys $B/qpaths x.desktop
  env -i HOME=$HOME XDG_DATA_HOME=$T/rel XDG_DATA_DIRS=$T/sys $B/qpaths x.desktop
  rm -rf "${T:?}" ;;
esac
