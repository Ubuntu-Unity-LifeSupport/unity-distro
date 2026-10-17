#!/bin/bash
# probe.sh STEP - UNITY-20261013-028 on target2 (as mike over ssh), unity-gtk4-menu 0.13 from live: which menus Papers
# has, which one the library chooses, and what the panel gets, in its start view and in its document view.
#   setup:     papers from the archive (target2 already at Clean-2 -> live), the test PDF in ~/b028
#   withdoc:   papers started with the PDF: the library's candidates and choice at realize, the exported menu
#   startview: papers started without a document, then the PDF opened in the same window through its Open dialog
#              (Ctrl+O, Ctrl+L, the path typed), with the candidates and the exported menu before and after
# Each run uses the session's environment with the library's debug log; every papers is ended before a run.
set -u
B=~/b028
sp=$(pgrep -x compiz | head -1)
mapfile -t envs < <(tr '\0' '\n' < /proc/$sp/environ | grep -v -E '^UNITY_GTK4_MENU_[A-Z]+=')
export $(printf '%s\n' "${envs[@]}" | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
win() { xdotool search --onlyvisible --class '^papers$' 2>/dev/null | head -1; }
dump() {
  local w; w=$(win)
  echo "  window ${w:-none} ($( [ -n "$w" ] && xdotool getwindowname $w))"
  [ -n "$w" ] && python3 $B/menudump.py $w | sed 's/^/    /'
}
liblog() { sed -E 's/^\[unity-gtk4-menu [0-9]+\] /    lib: /' $1; }
start() {   # $1 log, $2.. arguments
  local log=$1; shift
  pkill -x papers; for i in $(seq 50); do pgrep -x papers >/dev/null || break; sleep 0.1; done
  rm -f $log
  env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=$log papers "$@" > /tmp/b028-papers.out 2>&1 &
  for i in $(seq 100); do [ -n "$(win)" ] && break; sleep 0.1; done
  sleep 4; xdotool windowactivate --sync $(win) 2>/dev/null; sleep 1
}
case $1 in
setup)
  echo "== $(date -u +%FT%TZ), boot $(uptime -s)"
  touch ~/.dirty; rm -f ~/.xsessionrc
  for i in $(seq 120); do sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || break; sleep 5; done
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q papers xdotool > /tmp/b028-inst.log 2>&1; echo "  install rc=$?"
  dpkg-query -W papers libunity-gtk4-menu0 libgtk-nocsd0 | sed 's/^/  /'
  ;;
withdoc)
  echo "== withdoc at $(date -u +%FT%TZ); $(dpkg-query -W -f='papers ${Version}, ' papers)$(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0)"
  start /tmp/b028-withdoc.log $B/doc028.pdf
  sleep 3; dump; liblog /tmp/b028-withdoc.log
  echo "  shown menu buttons now (accessible names, from the window's own tree, not available without a11y): see the export above"
  pkill -x papers
  ;;
startview)
  echo "== startview at $(date -u +%FT%TZ)"
  # keys are typed below: the session must not be locked (light-locker took them as a password once)
  loginctl unlock-session "$(loginctl show-user "$USER" -p Display --value)"; xset s off -dpms
  gsettings set org.gnome.desktop.screensaver lock-enabled false; gsettings set org.gnome.desktop.session idle-delay 0
  rm -f /tmp/b028-second.log; start /tmp/b028-start.log
  echo "-- the start view"; dump; echo "  window pid $(xdotool getwindowpid $(win))"; liblog /tmp/b028-start.log
  # Papers runs one process per document (a second `papers file.pdf` is a process of its own, logs/02): the start
  # view becomes a document view in the same window only through its own Open dialog
  # (the dialog is xdg-desktop-portal-gtk's window and opens behind Papers, unfocused: activate it first)
  w=$(win); xdotool windowactivate --sync $w key --clearmodifiers ctrl+o; sleep 2
  fc=$(xdotool search --onlyvisible --class '^xdg-desktop-portal-gtk$' | head -1); echo "  file chooser window ${fc:-none}"
  xdotool windowactivate --sync $fc key --clearmodifiers ctrl+l; sleep 1
  xdotool type --delay 30 "$B/doc028.pdf"; sleep 1; xdotool key Return; sleep 6
  echo "-- after opening the PDF in the same instance"; dump; gnome-screenshot -w -f /tmp/b028-open.png 2>/dev/null
  echo "  windows: $(for w in $(xdotool search --onlyvisible --class '^papers$'); do echo -n "$w pid $(xdotool getwindowpid $w) ($(xdotool getwindowname $w)) "; done)"
  echo "  papers processes: $(pgrep -x papers | xargs)"; ls /tmp/b028-*.log | sed 's/^/  log: /'
  echo "  library log since the start view:"; liblog /tmp/b028-start.log
  pkill -x papers
  ;;
esac
