#!/bin/bash
# hud-alt.sh - the Unity 7 HUD as a user drives it, on target2 (run as mike over ssh, in the Unity session).
# Phase "prep": a Terminal focused, dbus-monitor on com.canonical.hud. The Alt tap itself comes from outside
# (vbox send_keys: a real keyboard event, which xdotool does not reproduce for Unity's Alt-tap detection);
# the query is typed here with xdotool (the vbox console cannot type Cyrillic).
# Phase "type <text>": types into the open HUD. Phase "report": windows, query objects, the calls Unity made.
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
HUD="--dest com.canonical.hud --object-path /com/canonical/hud"
case "$1" in
prep)
  C=$(pgrep -x compiz); (cat /proc/$C/environ; printf 'setsid\0sh\0-c\0gnome-terminal\0') > ~/.hud-args
  xargs -0 -a ~/.hud-args env -i > /dev/null 2>&1 < /dev/null &
  sleep 6; T=$(xdotool search --onlyvisible --name "mike@target2" | tail -1); xdotool windowactivate --sync $T
  nohup dbus-monitor --session "interface=com.canonical.hud" > /tmp/hudmon.txt 2>&1 < /dev/null &
  echo "terminal $T monitor $!" ;;
type)
  xdotool type --delay 150 "$2" ;;
report)
  echo "terminal windows: $(xdotool search --onlyvisible --name 'mike@target2' | xargs)"
  echo "query objects: $(gdbus introspect --session $HUD/query 2>/dev/null | grep -o 'node [0-9]*' | xargs)"
  echo "hud-service pid $(pgrep -x hud-service)"
  grep -A2 -E 'member=(StartQuery|CloseQuery|ExecuteQuery)' /tmp/hudmon.txt | grep -v '^--' \
    | sed -E 's/.*time=([0-9.]+).*member=(\w+).*/\1 \2/' | paste -sd' ' | sed -E 's/ ([0-9]{10}\.)/\n\1/g'
  journalctl --user -b --no-pager -t hud-service | tail -5 ;;
esac
