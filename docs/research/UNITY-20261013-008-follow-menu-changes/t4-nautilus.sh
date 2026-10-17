#!/bin/bash
# t4-nautilus.sh STEP [ARGS] - on target2, in the running Unity session: does Nautilus's exported menu follow its
# Undo item? Judged from the export (menudump.py, a D-Bus client as the panel) and the HUD (hudq.py), not from
# screenshots. F2, Enter, Ctrl+Z and Ctrl+N come from the host (vbox send_keys): xdotool's F2 opens Unity's run
# dialog on this keymap instead of reaching the window.
#   start [LIB]     end every Nautilus, make ~/b008/r with alpha/beta/gamma.txt, start Nautilus there with LIB
#                   preloaded instead of the session's unity-gtk4-menu (default: the installed one), activate it
#   select W K NAME activate window W (1 = the first, 2 = the newest) and select its K-th file (Home, then Right);
#                   NAME is typed after F2 by `type`
#   type NAME       select the old name in the rename field and type NAME (after the host's F2)
#   api FILE NEW    rename FILE to NEW through org.gnome.Nautilus.FileOperations2 RenameURI
#   show LABEL      the files, the Undo/Redo items each Nautilus window exports, the HUD's results
#   log             the library's log
set -u
B=~/b008; D=$B/r
SYS=/usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0
LOG=/tmp/t4-naut.log
sp=$(pgrep -x compiz)
mapfile -t envs < <(tr '\0' '\n' < /proc/$sp/environ | grep -v -E '^(LD_PRELOAD|UNITY_GTK4_MENU_[A-Z]+)=')
export $(printf '%s\n' "${envs[@]}" | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
windows() { xdotool search --onlyvisible --class org.gnome.Nautilus 2>/dev/null | sort -n; }

case $1 in
start)
  LIB=${2:-$SYS}; rm -f $LOG
  envs+=("LD_PRELOAD=$LIB:/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0" UNITY_GTK4_MENU_DEBUG=1 "UNITY_GTK4_MENU_LOG=$LOG")
  echo "== $(date -u +%FT%TZ); $(dpkg-query -W -f='nautilus ${Version}' nautilus); lib $LIB sha256 $(sha256sum < $LIB | cut -c1-16)"
  pkill -x nautilus; for i in $(seq 50); do pgrep -x nautilus >/dev/null || break; sleep 0.1; done
  mkdir -p $D; rm -f -- "$D"/*; for f in alpha beta gamma; do echo $f > $D/$f.txt; done
  env -i "${envs[@]}" nautilus --new-window $D > /tmp/t4-naut.out 2>&1 &
  for i in $(seq 100); do [ -n "$(windows)" ] && break; sleep 0.1; done
  sleep 3; xdotool windowactivate --sync $(windows | tail -1); sleep 1
  ;;
select)
  w=$(windows | if [ "$2" = 1 ]; then head -1; else tail -1; fi)
  xdotool windowactivate --sync $w; sleep 0.7; xdotool key Home
  for i in $(seq $(( $3 - 1 ))); do xdotool key Right; done
  sleep 0.5
  ;;
type)
  xdotool key ctrl+a; xdotool type --delay 60 "$2"; sleep 0.3
  ;;
api)
  gdbus call --session -d org.gnome.Nautilus -o /org/gnome/Nautilus/FileOperations2 \
    -m org.gnome.Nautilus.FileOperations2.RenameURI "file://$D/$2" "$3" '{}' >/dev/null
  echo "  RenameURI rc=$?"; sleep 2
  ;;
show)
  echo "-- $2 ($(date -u +%T)Z)"
  echo "  files: $(ls $D | tr '\n' ' ')"
  for w in $(windows); do
    echo "  window $w ($(xdotool getwindowname $w)):"
    python3 $B/menudump.py $w | grep -i -E "^window|отмен|повтор|undo|redo" | sed 's/^ */    export: /'
  done
  python3 $B/hudq.py "переименование" | sed 's/^/  /'
  ;;
log)
  echo "-- library log"
  sed -E 's/^\[unity-gtk4-menu [0-9]+\] /  lib: /' $LOG | grep -v -E "candidate [0-9]+ at depth"
  ;;
esac
