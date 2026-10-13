#!/bin/sh
# UNITY-20260928-019: from mike's autologin session to a first utest login
# through lightdm-gtk-greeter: log mike out, pick utest in the user list
# (screen coordinates of the 1280x800 greeter on target), type the password.
# Run as root. Usage: first-login.sh PASSWORD
set -u
PW=${1:?password}
G="env DISPLAY=:0 XAUTHORITY=/var/run/lightdm/root/:0"
setpriv --reuid=mike --regid=mike --init-groups env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager \
  --method org.gnome.SessionManager.Logout 1 >/dev/null
i=0; until pgrep -x lightdm-gtk-gre >/dev/null || [ $i -ge 60 ]; do sleep 1; i=$((i+1)); done
sleep 8
$G xdotool mousemove 689 365 click 1; sleep 1.5
$G xdotool mousemove 640 390 click 1; sleep 1.5
$G xdotool mousemove 689 408 click 1; sleep 0.5
$G xdotool type --delay 80 "$PW"; $G xdotool key Return
i=0; until loginctl list-sessions --no-legend | awk '$3=="utest" && $4=="seat0"' | grep -q . || [ $i -ge 60 ]; do sleep 1; i=$((i+1)); done
echo "first login: utest on seat0 after ${i}s"
