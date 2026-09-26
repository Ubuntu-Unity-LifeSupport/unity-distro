#!/bin/bash
# Known issue #3, #1-related hypothesis: do clicks survive mid-session events
# around the settings daemon and the session? Each condition, then a real click
# on the sensor (tablet, evdev) and the grab probe. Agent A.
. ~/envt.sh
node() { grep -l "$1" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5; }
M=/dev/input/$(node "ImExPS/2")
wiggle() { sudo ~/evseq.py $M 'move 30 10 5' 'move -30 -10 5'; }
S=$(loginctl list-sessions --no-legend | awk '$3=="mike" && $4=="seat0"{print $1}')
check() { wiggle; sleep 1; echo "$1: $(~/clickcheck.sh)"; }
check baseline
systemctl --user restart unity-settings-daemon.service; sleep 6; check "u-s-d restart"
python3 ~/steal-idle.py 2 >/dev/null; sleep 1; check "IdleMonitor name stolen and returned"
xset dpms force off; sleep 3; wiggle; sleep 2; check "DPMS off, woken by real motion"
loginctl lock-session $S; sleep 4; echo "locked: $(~/grab-probe)"; loginctl unlock-session $S; sleep 4; check "lock + unlock (logind)"
