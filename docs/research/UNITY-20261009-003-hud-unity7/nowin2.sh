#!/bin/bash
# nowin2.sh - UNITY-20261009-003, the null m_windowToken path: hud-service forgets the focused window when
# window-stack-bridge leaves the bus (ApplicationListImpl::serviceUnregistered) or when the focused application's
# last window closes (WindowDestroyed). Two tries, each followed at once by a legacy StartQuery + ExecuteQuery(0):
#   A. window-stack-bridge killed with SIGKILL (its user unit restarts it)
#   B. a terminal is the only application window and is closed; the query runs before any other window is focused
set -u
B=~/b0309
export DISPLAY=:0
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
hudpid() { pgrep -x hud-service | head -1; }
ensure() { gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud \
  --method org.freedesktop.DBus.Properties.Get com.canonical.hud OpenQueries > /dev/null 2>&1; sleep 2; }
case ${1:-A} in
A)
  ensure; p=$(hudpid); b=$(pgrep -x window-stack-br)
  echo "== A: hud-service $p, window-stack-bridge $b"
  kill -9 $b
  python3 $B/hudexec.py "" --key-zero
  sleep 3; echo "hud-service before $p, after $(hudpid); bridge now $(pgrep -x window-stack-br)" ;;
B)
  for a in gnome-terminal- nautilus gnome-text-edit soffice.bin; do pkill -x $a; done; sleep 2
  (env -i "${envs[@]}" setsid sh -c gnome-terminal > /dev/null 2>&1 < /dev/null &); sleep 6
  w=$(xdotool search --onlyvisible --name "mike@target2" | tail -1); xdotool windowactivate --sync $w; sleep 1
  ensure; p=$(hudpid)
  echo "== B: hud-service $p, terminal window $w the only application window"
  xdotool windowclose $w
  python3 $B/hudexec.py "" --key-zero
  sleep 3; echo "hud-service before $p, after $(hudpid)" ;;
C)
  # C. the query that starts hud-service: SIGTERM to hud-service, then StartQuery (D-Bus activation) and at once
  #    ExecuteQuery(0), before the service may have learnt the focused window
  (env -i "${envs[@]}" setsid sh -c gnome-terminal > /dev/null 2>&1 < /dev/null &); sleep 6
  w=$(xdotool search --onlyvisible --name "mike@target2" | tail -1); xdotool windowactivate --sync $w; sleep 1
  ensure; p=$(hudpid)
  echo "== C: hud-service $p stopped; terminal window $w focused"
  kill $p; while pgrep -x hud-service > /dev/null; do sleep 0.2; done
  python3 $B/hudexec.py "" --key-zero
  sleep 3; echo "hud-service before $p, after $(hudpid)" ;;
esac
journalctl --user --since "-20 s" --no-pager | grep -E "hud-service" | tail -4
