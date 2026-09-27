#!/bin/bash
# UNITY-20260927-005 (agent A): deterministic reproduction of known issue #1,
# independent of which launcher's instance survived the login.
# 1. stop every running unity-settings-daemon (systemd unit and the
#    xdg-autostart copy), start one fresh instance from the unit, wait until
#    its cursor plugin has hidden the pointer;
# 2. take org.gnome.Mutter.IdleMonitor away for 2 s (steal-idle.py);
# 3. move the real PS/2 mouse (evdev node found by name);
# 4. report only what the plugin logged AFTER the move: "show" = pass,
#    nothing (pointer stays hidden) = fail. NOSTEAL=1 skips step 2 (control).
. ~/envt.sh
A='app-unity\x2dsettings\x2ddaemon@autostart.service'
systemctl --user stop unity-settings-daemon.service "$A" 2>/dev/null
for i in $(seq 1 20); do pgrep -x unity-settings- >/dev/null || break; sleep 0.5; done
systemctl --user start unity-settings-daemon.service
P=; for i in $(seq 1 40); do P=$(pgrep -x unity-settings- | head -1); [ -n "$P" ] && grep -q "Attempting to hide" /tmp/usd-$P.log 2>/dev/null && break; sleep 0.5; done
sleep 2
v=$(dpkg-query -W -f '${Version}' unity-settings-daemon)
echo "pid $P ($v), instances: $(pgrep -xc unity-settings-), hidden at start: $(grep -c 'Attempting to hide' /tmp/usd-$P.log)"
[ -n "$NOSTEAL" ] && echo "  control: name not taken" || python3 ~/steal-idle.py 2; sleep 1
echo "  $(grep -E 'IdleMonitor' /tmp/usd-$P.log | tail -2 | cut -c40-140 | tr '\n' ' ')"
n=$(wc -l < /tmp/usd-$P.log)
N=$(grep -l "ImExPS/2" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5)
x0=$(xdotool getmouselocation | cut -d' ' -f1-2); sudo ~/evinject.py /dev/input/$N 8 4 2; sleep 1.5; x1=$(xdotool getmouselocation | cut -d' ' -f1-2)
after=$(tail -n +$((n + 1)) /tmp/usd-$P.log | grep -oE 'Attempting to (hide|show) the cursor|became active' | tr '\n' ';')
r=FAIL; echo "$after" | grep -q "Attempting to show" && r=PASS
echo "  moved $N [$x0]->[$x1]; after the move: ${after:-nothing} => $r"
