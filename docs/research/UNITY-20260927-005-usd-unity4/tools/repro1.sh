#!/bin/bash
# Deterministic reproduction of known issue #1 (agent A): restart the settings
# daemon (its cursor plugin hides the pointer), take the IdleMonitor name away
# and give it back, then move the real PS/2 mouse. Prints what the plugin did.
. ~/envt.sh
systemctl --user restart unity-settings-daemon.service
for i in $(seq 1 30); do P=$(pgrep -x unity-settings- | head -1); [ -n "$P" ] && grep -q "Attempting to hide" /tmp/usd-$P.log 2>/dev/null && break; sleep 1; done
sleep 2; echo "pid $P ($(dpkg -l unity-settings-daemon | awk '/^ii/{print $3}')), instances: $(pgrep -xc unity-settings-)"
python3 ~/steal-idle.py 2
sleep 1; grep -E "IdleMonitor" /tmp/usd-$P.log | tail -2 | cut -c40-160
N=$(grep -l "ImExPS/2" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5)
x0=$(xdotool getmouselocation | cut -d' ' -f1-2); sudo ~/evinject.py /dev/input/$N 8 4 2; sleep 1; x1=$(xdotool getmouselocation | cut -d' ' -f1-2)
echo "moved $N [$x0]->[$x1]; plugin: $(grep -E 'Attempting to (hide|show)|became active' /tmp/usd-$P.log | tail -1 | cut -c60-160)"
