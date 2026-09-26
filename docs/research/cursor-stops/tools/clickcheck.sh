#!/bin/bash
# Does a real click reach an application? (known issue #3, agent A)
# Clicks the centre of the "clicksensor" window with the USB tablet (evdev),
# reports how many presses the sensor recorded and whether a pointer grab is held.
. ~/envt.sh
node() { grep -l "$1" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5; }
W=$(xdotool search --name '^clicksensor$' | head -1)
[ -z "$W" ] && { (setsid nohup ~/clicksensor.py /tmp/clicks.log >/dev/null 2>&1 &) ; sleep 2; W=$(xdotool search --name '^clicksensor$' | head -1); }
eval $(xdotool getwindowgeometry --shell $W); cx=$((X + WIDTH / 2)); cy=$((Y + HEIGHT / 2))
before=$(wc -l < /tmp/clicks.log 2>/dev/null || echo 0)
sudo ~/evclick.py /dev/input/$(node "USB Tablet") $cx $cy left; sleep 0.7
after=$(wc -l < /tmp/clicks.log)
echo "click@$cx,$cy reached=$((after - before)) $(~/grab-probe)"
