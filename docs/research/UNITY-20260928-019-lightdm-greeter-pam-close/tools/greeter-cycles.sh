#!/bin/sh
# UNITY-20260928-019: N cycles of "log the test user out, wait for the
# greeter, log in again through lightdm-gtk-greeter", with a state snapshot
# after every login (what a skipped greeter PAM close could leave behind).
# Run as root on target while tools/greeter-close-trace.bt runs.
# Usage: greeter-cycles.sh N USER PASSWORD
# Based on UNITY-20260927-004 tools/login-cycle.sh. The test user exists only
# for the test and is removed afterwards. The greeter must already have USER
# preselected (one login by name before the first cycle).
set -u
N=${1:?cycles}; U=${2:?user}; PW=${3:?password}
G="env DISPLAY=:0 XAUTHORITY=/var/run/lightdm/root/:0"

snapshot() {
  echo "--- state after cycle $1 ($(date -u +%H:%M:%S.%NZ | cut -c1-12)Z)"
  loginctl list-sessions --no-legend | sed 's/^/sessions: /'
  loginctl list-users --no-legend | sed 's/^/users: /'
  for s in $(loginctl list-sessions --no-legend | awk '{print $1}'); do
    loginctl show-session "$s" -p Id -p Name -p Class -p State -p Scope -p Leader | paste -sd' ' | sed 's/^/session: /'
  done
  echo "lightdm-uid processes: $(ps -u lightdm -o pid=,comm= | paste -sd' ')"
  echo "user@109: $(systemctl is-active user@109.service) runtime-dir: $(ls -d /run/user/109 2>/dev/null || echo none)"
  echo "greeter scopes: $(systemctl list-units --all --no-legend 'session-*.scope' | awk '{print $1, $3, $4}' | paste -sd',')"
  echo "lightdm Xauthority entries: $(for f in /var/lib/lightdm/.Xauthority /var/run/lightdm/lightdm/xauthority; do [ -e $f ] && printf '%s:%s ' $f "$(xauth -f $f list 2>/dev/null | wc -l)"; done)"
  # does the greeter's cookie, if still in lightdm's file, open the display
  # the user session now runs on (same X server, same cookie)?
  if setpriv --reuid=lightdm --regid=lightdm --clear-groups env XAUTHORITY=/var/lib/lightdm/.Xauthority DISPLAY=:0 xdpyinfo >/dev/null 2>&1; then
    echo "uid lightdm with its .Xauthority opens :0: YES"; else echo "uid lightdm with its .Xauthority opens :0: no"; fi
  echo "journal 'session closed for user lightdm' since cycle start: $(journalctl -q --since "@$2" -t lightdm -g 'session closed for user lightdm' | wc -l)"
  echo "journal 'session opened for user lightdm' since cycle start: $(journalctl -q --since "@$2" -t lightdm -g 'session opened for user lightdm' | wc -l)"
}

for c in $(seq 1 "$N"); do
  start=$(date +%s)
  logger -t ldcycle "cycle $c: logout $U"
  # cycle 1 may log out someone else (FIRST=mike after an autologin); the
  # greeter still preselects the last user it logged in (USER)
  O=$U; [ "$c" = 1 ] && O=${FIRST:-$U}
  setpriv --reuid="$O" --regid="$O" --init-groups env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u "$O")/bus \
    gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager \
    --method org.gnome.SessionManager.Logout 1 >/dev/null
  # the old session must be off seat0 first, or the login check below sees it
  i=0; while loginctl list-sessions --no-legend | awk -v u="$O" '$3==u && $4=="seat0"' | grep -q . && [ $i -lt 60 ]; do sleep 1; i=$((i+1)); done
  logger -t ldcycle "cycle $c: $O off seat0 after ${i}s"
  i=0; until pgrep -x lightdm-gtk-gre >/dev/null || [ $i -ge 60 ]; do sleep 1; i=$((i+1)); done
  sleep 8
  logger -t ldcycle "cycle $c: greeter up after ${i}s, logging in"
  $G xdotool type --delay 80 "$PW"; $G xdotool key Return
  i=0; until loginctl list-sessions --no-legend | awk -v u="$U" '$3==u && $4=="seat0"' | grep -q . && ! pgrep -x lightdm-gtk-gre >/dev/null || [ $i -ge 90 ]; do sleep 1; i=$((i+1)); done
  logger -t ldcycle "cycle $c: $U session on seat0, greeter gone after ${i}s"
  echo "cycle $c: $U session on seat0, greeter gone after ${i}s"
  sleep 35
  snapshot "$c" "$start"
done
