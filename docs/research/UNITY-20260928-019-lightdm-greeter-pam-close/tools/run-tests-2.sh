#!/bin/sh
# UNITY-20260928-019: second pass of T3, T4 and T6 (the first pass had too
# few greeter stops: logouts refused by cinnamon-session), then T5. Same
# setup as run-tests.sh; the greeter preselects utest.
# Usage: run-tests-2.sh PASSWORD
set -u
PW=${1:?password}
H=/home/mike
phase() {
  name=$1; n=$2; shift 2
  echo "=== phase $name ($n cycles) $(date -u +%H:%M:%SZ)"
  logger -t ld019phase "phase $name start"
  if [ $# -gt 0 ]; then
    systemd-run --unit=ld019force-$name "$@" >/dev/null 2>&1; sleep 8
  fi
  sh $H/greeter-cycles.sh "$n" utest "$PW"
  [ $# -gt 0 ] && systemctl stop ld019force-$name
  logger -t ld019phase "phase $name end"
}
phase T3b-forced-in-pam_systemd-close 4 /usr/bin/bpftrace --unsafe $H/force-sigterm-at.bt close
phase T4b-forced-at-pam_end 4 /usr/bin/bpftrace --unsafe $H/force-sigterm-at.bt end
sh $H/stall-close.sh on
phase T6b-stalled-close-forced-stage1 3 /usr/bin/bpftrace --unsafe $H/force-late-sigterm.bt
sh $H/stall-close.sh off
# T5: one SIGTERM into the next greeter session-child before its greeter
# exists; the greeter will not start, so no login is attempted
echo "=== phase T5-preexec $(date -u +%H:%M:%SZ)"
logger -t ld019phase "phase T5-preexec start"
systemd-run --unit=ld019force-T5 /usr/bin/bpftrace --unsafe $H/force-sigterm-at.bt preexec >/dev/null 2>&1; sleep 8
sid=$(loginctl list-sessions --no-legend | awk '$4=="seat0" && $6=="user" {print $1}')
loginctl terminate-session "$sid"
sleep 30
echo "greeter running after T5: $(pgrep -x lightdm-gtk-gre >/dev/null && echo yes || echo no)"
loginctl list-sessions --no-legend | sed 's/^/T5 sessions: /'
systemctl stop ld019force-T5
logger -t ld019phase "phase T5-preexec end"
echo "=== done $(date -u +%H:%M:%SZ)"
