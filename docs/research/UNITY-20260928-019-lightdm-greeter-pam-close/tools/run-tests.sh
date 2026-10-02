#!/bin/sh
# UNITY-20260928-019: tests T2, T1, T3, T4, T6 of the evidence card in one
# go, on whatever lightdm is installed, while tools/greeter-close-trace.bt
# runs as unit ld019trace. Each phase starts its forcing script (if any) as
# its own unit, runs greeter cycles, and stops it again. Output: journal of
# this unit (cycles, snapshots) + ld019trace (SUMMARY) + ld019force-* units.
# Run as root after a boot with mike logged in automatically.
# Usage: run-tests.sh PASSWORD
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
# first cycle logs mike (autologin) out; the greeter preselects utest
FIRST=mike; export FIRST
phase T2-forced-stage1 4 /usr/bin/bpftrace --unsafe $H/force-late-sigterm.bt
unset FIRST
phase T1-natural 12
phase T3-forced-in-pam_systemd-close 3 /usr/bin/bpftrace --unsafe $H/force-sigterm-at.bt close
phase T4-forced-at-pam_end 3 /usr/bin/bpftrace --unsafe $H/force-sigterm-at.bt end
sh $H/stall-close.sh on
phase T6-stalled-close-forced-stage1 3 /usr/bin/bpftrace --unsafe $H/force-late-sigterm.bt
sh $H/stall-close.sh off
echo "=== done $(date -u +%H:%M:%SZ)"
