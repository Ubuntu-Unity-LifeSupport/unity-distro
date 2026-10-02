#!/bin/bash
# UNITY-20261002-002 (Design Challenger D6c): keyboard-toggle-race.sh of
# UNITY-20260928-022 with unity-settings-daemon running under valgrind in
# the live session instead of its systemd unit (valgrind also widens the
# start window, so the fixed path is exercised naturally). Output: the
# valgrind log (argument) and the race script's report on stdout.
# usage: race-under-valgrind.sh LOGFILE   (needs ~/kbdrace.py in /tmp and
# ~/keyboard-toggle-race.sh, as the -022 tools are installed on target)
. ~/envt.sh; L=${1:?logfile}
C=$(pgrep -x compiz)
eval "export $(tr '\0' '\n' < /proc/$C/environ | grep -E '^(DISPLAY|XAUTHORITY|XDG_CURRENT_DESKTOP|XDG_SESSION_TYPE|XDG_SESSION_ID|DESKTOP_SESSION|GDMSESSION)=' | tr '\n' ' ')"
systemctl --user stop unity-settings-daemon.service 'app-unity\x2dsettings\x2ddaemon@autostart.service' 2>/dev/null
sleep 2
G_DEBUG=gc-friendly setsid valgrind --time-stamp=yes --log-file="$L" --num-callers=12 --track-origins=no \
  /usr/lib/unity-settings-daemon/unity-settings-daemon > /tmp/usd-vg-race.out 2>&1 < /dev/null &
for i in $(seq 1 180); do
  o=$(gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
      --method org.freedesktop.DBus.GetNameOwner org.gnome.SettingsDaemon.Power 2>/dev/null)
  [ -n "$o" ] && break; sleep 1; done
echo "u-s-d $(dpkg-query -W -f '${Version}' unity-settings-daemon) under valgrind: Power owner after ${i}s: $o"
cp ~/kbdrace.py /tmp/kbdrace.py
sh ~/keyboard-toggle-race.sh
echo "Power owner after the race: $(gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetNameOwner org.gnome.SettingsDaemon.Power 2>&1 | cut -c1-60)"
pkill -TERM -x memcheck-amd64- 2>/dev/null; sleep 8
grep -E "ERROR SUMMARY|definitely lost|Invalid (read|write|free)" "$L" | tail -5
systemctl --user start unity-settings-daemon.service; sleep 6
echo "u-s-d back under systemd: $(pgrep -x unity-settings-)"
