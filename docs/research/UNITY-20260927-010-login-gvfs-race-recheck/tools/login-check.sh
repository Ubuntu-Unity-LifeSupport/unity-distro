#!/bin/sh
# UNITY-20260927-010: for one boot's graphical login of mike (default: this
# boot; or journalctl's -b offset as $1) - was a gvfs-daemon start killed
# (stopped) within 120 s of its first start, and how many D-Bus activations of
# org.gtk.vfs.Daemon timed out? Run as root >= 150 s after the login.
B=${1:-0}
J="journalctl -b $B --no-pager -o short-unix"
first=$($J | grep -m1 "Starting gvfs-daemon.service" | cut -d. -f1)
killed=0
if [ -n "$first" ]; then
  killed=$($J | awk -v t="$first" '{s=int($1)} s>=t && s<t+120 && /Stopped gvfs-daemon.service/ {n++} END {print n+0}')
fi
timeouts=$($J | grep -c "Failed to activate service 'org.gtk.vfs.Daemon'")
clients=$($J | grep -c "StartServiceByName .*org.gtk.vfs.Daemon\|StartServiceByName для org.gtk.vfs.Daemon")
inject=$($J -t u010 | grep -c "activation requested")
login=$($J | grep -m1 "New session .* of user .mike." | awk '{print strftime("%T", $1)}' 2>/dev/null)
echo "boot $B ($(journalctl -b $B -o short-iso --no-pager | head -1 | cut -c1-19)) login $login: injected=$inject gvfs-daemon killed at start=$killed dbus activation timeouts=$timeouts client proxy timeouts=$clients"
