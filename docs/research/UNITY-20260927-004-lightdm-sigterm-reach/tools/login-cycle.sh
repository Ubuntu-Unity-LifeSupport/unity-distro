#!/bin/sh
# UNITY-20260927-004: N cycles of "log the test user out, wait for the
# greeter, log in again through lightdm-gtk-greeter". Run as root on target
# while tools/ld-sigterm-trace.bt runs. Usage: login-cycle.sh N PASSWORD
# (the test user utest exists only for this test and is removed afterwards).
set -u
N=${1:?cycles}; PW=${2:?password}
G="env DISPLAY=:0 XAUTHORITY=/var/run/lightdm/root/:0"
for c in $(seq 1 "$N"); do
  logger -t ldcycle "cycle $c: logout utest"
  [ "$c" = 1 ] && pgrep -x lightdm-gtk-gre >/dev/null && logger -t ldcycle "cycle 1: greeter already up" || setpriv --reuid=utest --regid=utest --init-groups env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus \
    gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager \
    --method org.gnome.SessionManager.Logout 1 >/dev/null
  i=0; until pgrep -x lightdm-gtk-gre >/dev/null || [ $i -ge 60 ]; do sleep 1; i=$((i+1)); done
  sleep 8
  logger -t ldcycle "cycle $c: greeter up after ${i}s, logging in"
  # lightdm-gtk-greeter preselects the last user (utest) and focuses the
  # password field; the first login (user "Другие...") was typed by hand
  $G xdotool type --delay 80 "$PW"; $G xdotool key Return
  i=0; until loginctl list-sessions --no-legend | awk '$3=="utest" && $4=="seat0"' | grep -q . && ! pgrep -x lightdm-gtk-gre >/dev/null || [ $i -ge 90 ]; do sleep 1; i=$((i+1)); done
  logger -t ldcycle "cycle $c: utest session on seat0, greeter gone after ${i}s"
  sleep 25
done
