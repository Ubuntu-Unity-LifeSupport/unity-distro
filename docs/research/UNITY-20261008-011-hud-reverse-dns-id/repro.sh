#!/bin/bash
# repro.sh STEP - UNITY-20261008-011 on target2, in the Unity session (run as mike over ssh).
#   open APP...     start each command (gnome-terminal, gnome-mines, ...) from the session's environment
#   stack           the window stack: (window, application id, focused) for every window
#   apps            hud-service's Applications property (one object per application id)
#   icon WINDOW Q   activate WINDOW, legacy StartQuery Q: the icon field hud-service puts in each suggestion
#   use WINDOW Q    activate WINDOW, execute the first HUD result for Q (usage.py), print the usage table
#   frequent WINDOW activate WINDOW, the empty HUD query's first results (frequent.py)
#   close           close every window opened by "open" (xdotool windowclose by pid)
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
stack() { gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack | grep -o "([0-9]*, '[^']*', [a-z]*" | grep -v compiz | tr '\n' ' '; echo; }
case $1 in
open)
  shift; P=$(pgrep -x compiz)
  for a in "$@"; do
    (cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "$a") > ~/.r11-args
    xargs -0 -a ~/.r11-args env -i > /dev/null 2>&1 < /dev/null &
    sleep 8
  done ;;
stack) stack ;;
apps) gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method org.freedesktop.DBus.Properties.Get com.canonical.hud Applications ;;
icon)
  xdotool windowactivate --sync $2; sleep 1
  gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud.StartQuery "$3" 3 | grep -o "'[^']*', <" | head -3 | tr '\n' ' '; echo
  gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud.StartQuery "$3" 3 | head -c 600; echo ;;
use)
  xdotool windowactivate --sync $2; sleep 1; python3 ~/b011/usage.py "$3"; sleep 2; xdotool key Escape; sleep 1 ;;
frequent)
  xdotool windowactivate --sync $2; sleep 1; python3 ~/b011/frequent.py ;;
close)
  for w in $(xdotool search --onlyvisible --class "gnome-terminal|gnome-mines|Mines|Terminal" 2>/dev/null); do xdotool windowclose $w 2>/dev/null; done ;;
esac
