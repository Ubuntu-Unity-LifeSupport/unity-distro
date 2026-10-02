#!/bin/bash
# Does a real click reach an application? (known issue #3, agent A)
# Clicks the centre of the "clicksensor" window with the USB tablet (evdev),
# reports how many presses the sensor recorded and whether a pointer grab is held.
. ~/envt.sh
node() { grep -l "$1" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5; }
W=$(xdotool search --onlyvisible --name '^clicksensor$' | head -1)
[ -z "$W" ] && { (setsid nohup ~/clicksensor.py /tmp/clicks.log >/dev/null 2>&1 &) ; sleep 2; W=$(xdotool search --onlyvisible --name '^clicksensor$' | head -1); }
# UNITY-20260927-040: with workspaces on, the sensor can be left on another
# viewport (after expo); bring it into the current one first
xdotool windowmove $W 100 100; sleep 0.3
eval $(xdotool getwindowgeometry --shell $W); cx=$((X + WIDTH / 2)); cy=$((Y + HEIGHT / 2))
before=$(wc -l < /tmp/clicks.log 2>/dev/null || echo 0)
# UNITY-20260927-040: CLICKAT=X,Y clicks there instead (replaying the first
# stuck run, whose check click landed on the launcher at 0,207)
[ -n "$CLICKAT" ] && { cx=${CLICKAT%%,*}; cy=${CLICKAT##*,}; }
sudo ~/evclick.py /dev/input/$(node "USB Tablet") $cx $cy left; sleep 0.7
after=$(wc -l < /tmp/clicks.log)
echo "click@$cx,$cy reached=$((after - before)) $(~/grab-probe)"
