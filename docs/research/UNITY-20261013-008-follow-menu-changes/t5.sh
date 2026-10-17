#!/bin/bash
# t5.sh STEP [ARGS] - on target2, in the running Unity session: an open panel menu while the application's menu
# changes (t5app.py), judged by events: popwatch2 (popwatch2.c) (the panel service's popups, each with its geometry), sync.sh (the panel's entry
# for the window), the application's change lines, the library's log. Keys come from the host (vbox send_keys):
# Alt+F10 opens the holder's menu; Down/Right open "Sub"; Escape closes.
#   start MODE [LIB]  end any t5app, start t5app.py MODE with LIB preloaded instead of the session's
#                     unity-gtk4-menu (default: the installed one), activate it, print the panel's entry
#   watch SECONDS     popwatch2 (popwatch2.c) for SECONDS in the background (started right before the key from the host)
#   end               what popwatch saw, the entry again, the change lines, the export now, the library's log;
#                     ends t5app
set -u
B=~/b008
SYS=/usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0
LOG=/tmp/t5.log
sp=$(pgrep -x compiz)
mapfile -t envs < <(tr '\0' '\n' < /proc/$sp/environ | grep -v -E '^(LD_PRELOAD|UNITY_GTK4_MENU_[A-Z]+)=')
export $(printf '%s\n' "${envs[@]}" | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
win() { xdotool search --onlyvisible --name '^t5app ' 2>/dev/null | tail -1; }
entry() { bash $B/sync.sh "$1" | grep -E "^==|win=$(win) " | sed 's/^/  /'; }

case $1 in
start)
  mode=$2; LIB=${3:-$SYS}; rm -f $LOG /tmp/t5-pop.txt
  for p in $(pgrep -x python3); do
    grep -q t5app.py /proc/$p/cmdline 2>/dev/null && kill $p; done; sleep 0.5
  envs+=("LD_PRELOAD=$LIB:/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0" UNITY_GTK4_MENU_DEBUG=1 "UNITY_GTK4_MENU_LOG=$LOG")
  echo "== $(date -u +%FT%TZ) t5app $mode; lib $LIB sha256 $(sha256sum < $LIB | cut -c1-16)"
  env -i "${envs[@]}" python3 $B/t5app.py $mode > /tmp/t5-app.out 2>&1 &
  for i in $(seq 100); do [ -n "$(win)" ] && break; sleep 0.1; done
  sleep 2; xdotool windowactivate --sync $(win); sleep 0.7
  echo "  window $(win), active $(xdotool getactivewindow)"
  entry "entry at start"
  ;;
watch)
  nohup $B/popwatch2 $(pgrep -x unity-panel-ser) $2 > /tmp/t5-pop.txt 2>&1 < /dev/null &
  sleep 0.6; echo "  popwatch: $(head -1 /tmp/t5-pop.txt)"
  ;;
end)
  echo "-- popwatch"; sed 's/^/  /' /tmp/t5-pop.txt
  entry "entry at the end"
  echo "-- the application's changes"; sed 's/^/  /' /tmp/t5-app.out | grep -v -E "portal|Inhibit"
  echo "-- the export now"; python3 $B/menudump.py $(win) | sed 's/^/  /'
  echo "-- library log"; sed -E 's/^\[unity-gtk4-menu [0-9]+\] /  lib: /' $LOG | grep -v -E "candidate [0-9]+ at depth"
  for p in $(pgrep -x python3); do grep -q t5app.py /proc/$p/cmdline 2>/dev/null && kill $p; done
  ;;
esac
