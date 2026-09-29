#!/bin/sh
# UNITY-20260928-019: third pass after Verifier round 1: more natural greeter
# stops (T1b), T5 at fork() with the handler installed (T5b), and user
# sessions stopped by the daemon on the patched build (T7 = runs/03 again).
# Starts from mike's autologin session. Usage: run-tests-3.sh PASSWORD
set -u
PW=${1:?password}
H=/home/mike
echo "=== phase T1b-natural (6 cycles) $(date -u +%H:%M:%SZ)"
logger -t ld019phase "phase T1b-natural start"
FIRST=mike sh $H/greeter-cycles.sh 6 utest "$PW"
logger -t ld019phase "phase T1b-natural end"

echo "=== phase T5b-prefork $(date -u +%H:%M:%SZ)"
logger -t ld019phase "phase T5b-prefork start"
systemd-run --unit=ld019force-T5b /usr/bin/bpftrace --unsafe $H/force-sigterm-at.bt prefork >/dev/null 2>&1; sleep 8
sid=$(loginctl list-sessions --no-legend | awk '$4=="seat0" && $6=="user" {print $1}')
loginctl terminate-session "$sid"
sleep 30
echo "greeter running after T5b: $(pgrep -x lightdm-gtk-gre >/dev/null && echo yes || echo no)"
loginctl list-sessions --no-legend | sed 's/^/T5b sessions: /'
systemctl stop ld019force-T5b
logger -t ld019phase "phase T5b-prefork end"

echo "=== phase T7-user-session-restart (6 restarts) $(date -u +%H:%M:%SZ)"
logger -t ld019phase "phase T7 start"
sh $H/restart-cycles.sh 6
logger -t ld019phase "phase T7 end"
echo "=== done $(date -u +%H:%M:%SZ)"
