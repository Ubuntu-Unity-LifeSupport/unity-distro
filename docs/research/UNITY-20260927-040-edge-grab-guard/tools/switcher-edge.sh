#!/bin/bash
# UNITY-20260927-001 (agent A): a click on a window border while Unity's
# Alt+Tab switcher holds its compiz grab ("unity-switcher"). Real devices only.
# Prints the pointer/keyboard grab state after Alt is released and whether a
# real click reaches the sensor window afterwards.
. ~/envt.sh
node() { grep -l "$1" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5; }
T=/dev/input/$(node "USB Tablet"); M=/dev/input/$(node "ImExPS/2"); K=/dev/input/$(node "AT Translated")
W=$(xdotool search --onlyvisible --class '^XTerm$' | head -1)
[ -z "$W" ] && { (setsid nohup xterm -title rtarget >/dev/null 2>&1 &); sleep 2; W=$(xdotool search --onlyvisible --class '^XTerm$' | head -1); }
xdotool windowmove $W 500 200 windowsize $W 400 300; sleep 0.7
eval $(xdotool getwindowgeometry --shell $W)
R=$(xprop -id $W _NET_FRAME_EXTENTS | grep -oE "[0-9]+, [0-9]+, [0-9]+, [0-9]+" | cut -d, -f2 | tr -d ' ')
bx=$((X + WIDTH + ${R:-0} / 2 + 1)); by=$((Y + HEIGHT / 2))
sudo ~/evclick.py $T $bx $by none; sleep 0.3
sudo ~/evkeys.py $K 'down LEFTALT' 'tap TAB' 'sleep 1.5'
sudo ~/evseq.py $M 'down left' 'sleep 0.3' 'up left' 'sleep 0.5'
during=$(~/grab-probe)
sudo ~/evkeys.py $K 'up LEFTALT' 'sleep 1'
echo "switcher-edge border@$bx,$by | during: $during | after alt up: $(~/grab-probe) | $(~/clickcheck.sh)"
