#!/bin/sh
# UNITY-20260927-004: with the greeter up, attach tools/ld-exit-alloc.bt to
# the greeter's session-child only, save its maps, log in (utest is
# preselected), and keep what the probe saw. Run as root on target.
# Usage: exit-alloc-once.sh PASSWORD OUTDIR
set -u
PW=${1:?password}; D=${2:?outdir}; mkdir -p "$D"
G="env DISPLAY=:0 XAUTHORITY=/var/run/lightdm/root/:0"
S=$(loginctl list-sessions --no-legend | awk '$3=="lightdm" && $4=="seat0"{print $1}')
SC=$(loginctl show-session "$S" -p Leader --value)
echo "greeter session $S, session-child $SC: $(tr '\0' ' ' < /proc/$SC/cmdline)" > "$D/info"
cp /proc/$SC/maps "$D/maps.$SC"
bpftrace -p "$SC" /home/mike/ld-exit-alloc.bt > "$D/probe.txt" 2>&1 &
BP=$!
sleep 8
$G xdotool type --delay 80 "$PW"; $G xdotool key Return
sleep 15
kill -INT $BP; sleep 2
journalctl -o short-precise --no-pager --since "-30s" _PID=$SC >> "$D/info" 2>&1
