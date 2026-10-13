#!/bin/bash
# UNITY-20260927-052 (agent A): run unity-settings-daemon under valgrind in
# the live session instead of its systemd unit, then let two IdleMonitor
# clients add a watch and exit. Output: the valgrind log.
# usage: [PAUSE=seconds before the clients] [INPUT=1] usd-valgrind.sh LOGFILE
# INPUT=1: real mouse input (PS/2 evdev node) after each departure, so the
# X event filter reads the XSync state between and after the frees.
. ~/envt.sh; L=$1
C=$(pgrep -x compiz)
eval "export $(tr '\0' '\n' < /proc/$C/environ | grep -E '^(DISPLAY|XAUTHORITY|XDG_CURRENT_DESKTOP|XDG_SESSION_TYPE|XDG_SESSION_ID|DESKTOP_SESSION|GDMSESSION)=' | tr '\n' ' ')"
systemctl --user stop unity-settings-daemon.service 'app-unity\x2dsettings\x2ddaemon@autostart.service' 2>/dev/null
setsid valgrind --time-stamp=yes --log-file="$L" --num-callers=12 --track-origins=no \
  /usr/lib/unity-settings-daemon/unity-settings-daemon > /tmp/usd-vg.out 2>&1 < /dev/null &
for i in $(seq 1 120); do
  o=$(gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
      --method org.freedesktop.DBus.GetNameOwner org.gnome.Mutter.IdleMonitor 2>/dev/null)
  [ -n "$o" ] && break; sleep 1; done
echo "IdleMonitor owner after ${i}s: $o"; echo "valgrind start + clients from: $(date +%T)"; sleep ${PAUSE:-5}
echo "first client at $(date +%T)"
N=$(grep -l "ImExPS/2" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5)
move() { [ -n "${INPUT:-}" ] && { sudo ~/evinject.py /dev/input/$N 8 4 2 >/dev/null; echo "input at $(date +%T)"; }; }
python3 ~/watch-client.py active; sleep 3; move; sleep 3; move; sleep 3
python3 ~/watch-client.py active; sleep 5; move; sleep 5; move; sleep 10
pkill -TERM -x memcheck-amd64- 2>/dev/null; sleep 5
systemctl --user start unity-settings-daemon.service
