#!/bin/bash
# target.sh STEP - UNITY-20260929-001 checks on target2, in the Unity session (run as mike over ssh).
# Steps:
#   versions        packages, binaries and their mappings (no "(deleted)")
#   writer N        start Writer N times (killed in between): the window stack's id for the document window and
#                   the bridge's signals for it (dbus-monitor)
#   use             execute the first HUD result for "Сохранить" (CreateQuery, ExecuteCommand) and print the
#                   usage table; the Save dialog is closed with Escape
#   frequent        Writer killed and started again, then an empty HUD query (frequent.py): its first results
#                   (the "most used" list the HUD shows when opened)
#   live            a CreateQuery as soon as the Writer window is visible, read at +0..+10 s (no reopening)
#   startcenter     the LibreOffice Start Center, then a new Writer document from it (ctrl+n): the stack's id
#                   for the window before and after
#   terminal        a terminal started and closed: the bridge's signals for it
#   bridge-restart  window-stack-bridge killed with SIGKILL (its unit restarts it), then startcenter again,
#                   and hud-service's answer for the focused window
#   bamf-kill       bamfdaemon killed: is window-stack-bridge still running, what does the stack give
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
stack() { gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack | grep -o "([0-9]*, '[^']*', [a-z]*" | grep -v compiz | tr '\n' ' '; echo; }
start_lo() { # $1 = writer | calc | "" (Start Center)
  P=$(pgrep -x compiz)
  (cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "libreoffice ${1:+--$1} --norestore") > ~/.ht-args
  xargs -0 -a ~/.ht-args env -i > /dev/null 2>&1 < /dev/null &
}
kill_lo() { pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep 2; }
wait_title() { local i=0; while ! xdotool search --onlyvisible --name "$1" >/dev/null 2>&1 && [ $i -lt 90 ]; do sleep 1; i=$((i+1)); done; }
bridge_signals() { # $1 raw capture, $2 xid
  grep -A2 -E "member=(WindowCreated|WindowDestroyed|FocusedWindowChanged)" "$1" | grep -E "member=|uint32|string" | paste - - - | grep -E "uint32 $2\b" | sed -E 's/.*member=(\S+)\s+uint32 ([0-9]+)\s+string "([^"]*)".*/\1(\2, \3)/' | tr '\n' ' '; echo
}
case $1 in
versions)
  dpkg-query -W hud libhud2 unity bamfdaemon libreoffice-writer
  for n in window-stack-br hud-service; do p=$(pgrep -x $n | head -1); echo "$n pid $p exe $(readlink /proc/$p/exe) sha256 $(sha256sum /proc/$p/exe | cut -c1-16) deleted $(grep -c '(deleted)' /proc/$p/maps)"; done ;;
writer|calc)
  for i in $(seq "${2:-1}"); do
    kill_lo
    dbus-monitor --session "interface='com.canonical.Unity.WindowStack'" > /tmp/t.raw 2>&1 & mon=$!; sleep 1
    start_lo $1; [ $1 = writer ] && wait_title "LibreOffice Writer" || wait_title "LibreOffice Calc"; sleep 6; kill $mon
    w=$(xdotool search --onlyvisible --name "LibreOffice $( [ $1 = writer ] && echo Writer || echo Calc)" | tail -1)
    echo "$1 start $i: window $w; stack: $(stack | grep -o "($w, '[^']*', [a-z]*")"; echo "   bridge: $(bridge_signals /tmp/t.raw $w)"
  done ;;
use)
  w=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1); xdotool windowactivate --sync $w; sleep 1
  python3 ~/b001/usage.py "Сохранить"; sleep 2; xdotool key Escape; sleep 1 ;;
frequent)
  kill_lo; start_lo writer; wait_title "LibreOffice Writer"; sleep 8
  w=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1); xdotool windowactivate --sync $w; sleep 1
  echo "window $w; stack: $(stack | grep -o "($w, '[^']*', [a-z]*")"
  python3 ~/b001/frequent.py ;;
live)
  kill_lo; start_lo writer; i=0; while ! xdotool search --onlyvisible --name "LibreOffice Writer" >/dev/null 2>&1 && [ $i -lt 600 ]; do sleep 0.1; i=$((i+1)); done
  xdotool windowactivate --sync $(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1)
  python3 ~/b001/livequery.py "Сохранить" /tmp/lq.txt; grep -E "\+[0-9]+s:|legacy" /tmp/lq.txt
  echo "stack after: $(stack)" ;;
startcenter)
  kill_lo
  dbus-monitor --session "interface='com.canonical.Unity.WindowStack'" > /tmp/t.raw 2>&1 & mon=$!; sleep 1
  start_lo ""; wait_title "LibreOffice"; sleep 6
  w=$(xdotool search --onlyvisible --name "LibreOffice" | tail -1); echo "start center window $w ($(xdotool getwindowname $w)); stack: $(stack)"
  xdotool windowactivate --sync $w; sleep 1; xdotool key ctrl+n; wait_title "LibreOffice Writer"; sleep 6; kill $mon
  w2=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1); echo "after ctrl+n: window $w2 ($(xdotool getwindowname $w2)); stack: $(stack)"
  echo "   bridge for $w2: $(bridge_signals /tmp/t.raw $w2)"
  echo "   HUD for the focused window: $(gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud.StartQuery 'Сохранить' 5 | grep -o '(Файл)' | wc -l) results with (Файл)" ;;
terminal)
  dbus-monitor --session "interface='com.canonical.Unity.WindowStack'" > /tmp/t.raw 2>&1 & mon=$!; sleep 1
  P=$(pgrep -x compiz); (cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "x-terminal-emulator") > ~/.ht-args2
  xargs -0 -a ~/.ht-args2 env -i > /dev/null 2>&1 < /dev/null &
  sleep 6; w=$(xdotool getactivewindow); echo "terminal window $w ($(xdotool getwindowname $w)); stack: $(stack | grep -o "($w, '[^']*', [a-z]*")"
  xdotool windowclose $w 2>/dev/null || xdotool key --window $w ctrl+d; sleep 3; kill $mon
  echo "   bridge for $w: $(bridge_signals /tmp/t.raw $w)" ;;
bridge-restart)
  p=$(pgrep -x window-stack-br); echo "stack before: $(stack)"; kill -9 $p; sleep 4
  echo "window-stack-bridge: old pid $p, now $(pgrep -x window-stack-br) ($(systemctl --user is-active window-stack-bridge.service))"
  bash "$0" startcenter ;;
bamf-kill)
  p=$(pgrep -x bamfdaemon); kill $p; sleep 5
  echo "bamfdaemon: old pid $p, now $(pgrep -x bamfdaemon || echo none); window-stack-bridge: $(pgrep -x window-stack-br || echo none)"
  echo "stack: $(stack 2>&1)"; journalctl --user --since "-30 s" --no-pager 2>/dev/null | grep -E "window-stack-bridge" | tail -5 ;;
esac
