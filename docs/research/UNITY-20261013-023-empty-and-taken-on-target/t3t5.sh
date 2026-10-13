#!/bin/bash
# t3t5.sh STEP TAG - on target2 in the Unity session (as mike over ssh), design tests 3 and 5 of UNITY-20261012-004
# with the installed unity-gtk4-menu. Keys come from the host (vbox send_keys) between the steps; the outcomes are
# read from events (the panel service's entry table via UNITY-20261012-003's sync.sh and its full Sync table, its
# popups via popwatch.sh, its ShowEntry/EntryActivated via dbus-monitor, and what hud-service returns for a query via
# hudq.py), not from screenshots.
#   t3-start TAG: gnome-tour (no menu) in the session's environment with the library's debug log, activated; its
#                 window properties, the panel's entries for it, the HUD's results for "a" and "tour" (hudq.py);
#                 popwatch.sh for 15 s and a dbus-monitor on the panel service.
#   t5-start TAG: takeover.py (no menu at realize, its own menubar 5 s after present) the same way; the entries
#                 for its window before and 7 s after (after it set its menubar); popwatch.sh for 15 s.
#   end TAG:      what popwatch saw, the HUD's results (the strings hud-service returned), the library's log, the
#                 panel's entries again; then the application is closed.
#   lim on|off:   com.canonical.Unity integrated-menus (locally integrated menus) for the next start.
set -u
step=$1; tag=${2:-x}
B3=~/b1203; B=~/b1204t
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
entries() { bash $B3/sync.sh "$tag-$1" | grep -E "win=$2" | sed 's/^/    /'; echo "    ($(bash $B3/sync.sh x | grep -c "win=$2") entries for window $2)"; }
start() {  # start TAG CLASS CMD...
  local class=$1; shift
  rm -f /tmp/ugm-$tag.log
  env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=/tmp/ugm-$tag.log "$@" > /tmp/app-$tag.out 2>&1 &
  echo $! > /tmp/app-$tag.pid
  for i in $(seq 100); do w=$(xdotool search --onlyvisible --class "$class" 2>/dev/null | tail -1); [ -n "$w" ] && break; sleep 0.1; done
  sleep 2; xdotool windowactivate --sync "$w" 2>/dev/null; sleep 0.5
  echo "$w" > /tmp/app-$tag.win
  echo "  $(date -u +%T)Z window $w ($(xdotool getwindowname "$w")), active $(xdotool getactivewindow)"
  echo "  $(xprop -id "$w" _GTK_MENUBAR_OBJECT_PATH 2>&1)"
}
case $step in
  lim) gsettings set com.canonical.Unity integrated-menus "$([ "$tag" = on ] && echo true || echo false)"
       echo "  integrated-menus: $(gsettings get com.canonical.Unity integrated-menus)" ;;
  t3-start)
    echo "== $tag t3 at $(date -u +%FT%TZ); $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0); integrated-menus $(gsettings get com.canonical.Unity integrated-menus)"
    start gnome-tour gnome-tour; w=$(cat /tmp/app-$tag.win)
    echo "  panel entries for the window:"; entries before "$w"
    python3 $B/hudq.py a; python3 $B/hudq.py tour
    nohup timeout 25 dbus-monitor --session "interface=com.canonical.Unity.Panel.Service" > /tmp/panel-$tag.txt 2>&1 < /dev/null &
    nohup bash $B3/popwatch.sh 15 > /tmp/pop-$tag.txt 2>&1 < /dev/null &
    sleep 0.6; echo "  popwatch: $(head -1 /tmp/pop-$tag.txt)" ;;
  t5-start)
    nohup timeout 40 dbus-monitor --session "interface=com.canonical.Unity.Panel.Service" > /tmp/panel-$tag.txt 2>&1 < /dev/null &
    echo "== $tag t5 at $(date -u +%FT%TZ); $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0); integrated-menus $(gsettings get com.canonical.Unity integrated-menus)"
    start takeover python3 $B/takeover.py 5; w=$(cat /tmp/app-$tag.win)
    echo "  panel entries for the window, before the takeover:"; entries before "$w"
    sleep 7; sed 's/^/  app: /' /tmp/app-$tag.out
    echo "  panel entries for the window, after:"; entries after "$w"
    nohup bash $B3/popwatch.sh 15 > /tmp/pop-$tag.txt 2>&1 < /dev/null &
    sleep 0.6; echo "  popwatch: $(head -1 /tmp/pop-$tag.txt)" ;;
  end)
    w=$(cat /tmp/app-$tag.win)
    echo "-- $tag end at $(date -u +%T)Z"
    echo "  popwatch:"; sed 's/^/    /' /tmp/pop-$tag.txt
    if [ -f /tmp/panel-$tag.txt ]; then
      echo "  panel service calls and signals:"
      grep -A2 -E 'member=(ShowEntry|EntryActivated)' /tmp/panel-$tag.txt | grep -E 'member=|string' | sed 's/^/    /' | head -12
      for id in $(grep -A1 -E 'member=ShowEntry' /tmp/panel-$tag.txt | grep -oE 'string "0x[0-9a-f]+"' | grep -oE '0x[0-9a-f]+' | sort -u); do
        echo "    entry $id is: $(gdbus call --session --dest com.canonical.Unity.Panel.Service.Desktop --object-path /com/canonical/Unity/Panel/Service --method com.canonical.Unity.Panel.Service.Sync | grep -oE "'[^']*', '$id', '[^']*', [^(]*" | head -1 | cut -c1-140)"
      done
    fi
    [ "${tag#t3}" != "$tag" ] && { python3 $B/hudq.py a; python3 $B/hudq.py tour; }
    echo "  library log:"; sed 's/^/    /' /tmp/ugm-$tag.log
    [ -s /tmp/app-$tag.out ] && sed 's/^/  app: /' /tmp/app-$tag.out
    echo "  panel entries now:"; entries end "$w"
    kill "$(cat /tmp/app-$tag.pid)" 2>/dev/null; true ;;
esac
