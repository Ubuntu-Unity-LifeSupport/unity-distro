#!/bin/sh
# UNITY-20260928-019: one more T6 cycle (stalled greeter close + forced late
# SIGTERM) to keep lightdm.log's line for it - the T7 restarts overwrote the
# log of the first T6 runs (backup-logs=false). Starts from mike's autologin
# session. Usage: run-tests-4.sh PASSWORD
set -u
PW=${1:?password}
H=/home/mike
echo "=== phase T6c-stalled-close-forced-stage1 (1 cycle) $(date -u +%H:%M:%SZ)"
sh $H/stall-close.sh on
systemd-run --unit=ld019force-T6c /usr/bin/bpftrace --unsafe $H/force-late-sigterm.bt >/dev/null 2>&1; sleep 8
FIRST=mike sh $H/greeter-cycles.sh 1 utest "$PW"
systemctl stop ld019force-T6c
sh $H/stall-close.sh off
journalctl -u ld019force-T6c -q -o cat | grep forcing
echo "--- lightdm.log"
grep -E "Session pid=.*(Sending SIGTERM|Terminated with signal|Exited with return value)" /var/log/lightdm/lightdm.log | tail -6
echo "=== done $(date -u +%H:%M:%SZ)"
