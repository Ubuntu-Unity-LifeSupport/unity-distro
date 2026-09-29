#!/bin/sh
# UNITY-20260928-019: short regression run on the gated build (release
# procedure): T2 (forced late SIGTERM, 3 cycles) and T1 (natural, 3 cycles)
# under tools/greeter-close-trace.bt. Starts from mike's autologin session with
# utest preselected in the greeter. Run as root. Usage: rt-gated.sh PASSWORD
set -u
PW=${1:?password}
H=/home/mike
echo "=== $(date -u +%FT%TZ) $(dpkg-query -W lightdm liblightdm-gobject-1-0 | paste -sd' ') boot $(uptime -s)"
systemd-run --unit=ld019rt-trace /usr/bin/bpftrace $H/greeter-close-trace.bt >/dev/null 2>&1; sleep 6
echo "=== T2 forced late SIGTERM"
systemd-run --unit=ld019rt-force /usr/bin/bpftrace --unsafe $H/force-late-sigterm.bt >/dev/null 2>&1; sleep 8
FIRST=mike sh $H/greeter-cycles.sh 3 utest "$PW"
systemctl stop ld019rt-force
echo "=== T1 natural"
sh $H/greeter-cycles.sh 3 utest "$PW"
systemctl stop ld019rt-trace
echo "=== forced"; journalctl -u ld019rt-force -q -o cat | grep forcing
echo "=== SUMMARY"; journalctl -u ld019rt-trace -q -o cat | grep SUMMARY
echo "=== done"
