#!/bin/bash
# Known issue #3, hypothesis: a window-border resize (compiz resize plugin, a
# pointer-only grab) is left grabbed when another button or the wheel is used
# during the drag (LP 1885435, LP 1644412). Real devices only: the tablet puts
# the pointer on the border, the PS/2 mouse presses, drags, adds buttons.
# usage: resize-grab.sh VARIANT      (agent A)
. ~/envt.sh; V=$1
node() { grep -l "$1" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5; }
T=/dev/input/$(node "USB Tablet"); M=/dev/input/$(node "ImExPS/2")
W=$(xdotool search --onlyvisible --class '^XTerm$' | head -1)
[ -z "$W" ] && { (setsid nohup xterm -title rtarget >/dev/null 2>&1 &); sleep 2; W=$(xdotool search --onlyvisible --class '^XTerm$' | head -1); }
xdotool windowmove $W 500 200 windowsize $W 400 300; sleep 0.7
eval $(xdotool getwindowgeometry --shell $W)
R=$(xprop -id $W _NET_FRAME_EXTENTS | grep -oE "[0-9]+, [0-9]+, [0-9]+, [0-9]+" | cut -d, -f2 | tr -d ' ')
bx=$((X + WIDTH + ${R:-0} / 2 + 1)); by=$((Y + HEIGHT / 2))
TOP=$(xprop -id $W _NET_FRAME_EXTENTS | grep -oE "[0-9]+, [0-9]+, [0-9]+, [0-9]+" | cut -d, -f3 | tr -d " ")
case $V in title*) bx=$((X + WIDTH / 2 + 40)); by=$((Y - ${TOP:-20} / 2));; esac
sudo ~/evclick.py $T $bx $by none; sleep 0.3
case $V in
  rmb)   sudo ~/evseq.py $M 'down left' 'move 20 0 4' 'down right' 'move 80 30 8' 'up right' 'move 10 0 2' 'up left' ;;
  rmb2)  sudo ~/evseq.py $M 'down left' 'move 20 0 4' 'down right' 'move 80 30 8' 'up left' 'move 10 0 2' 'up right' ;;
  wheel) sudo ~/evseq.py $M 'down left' 'move 30 10 4' 'wheel 1' 'wheel -1' 'move 20 0 2' 'up left' ;;
  mid)   sudo ~/evseq.py $M 'down left' 'move 30 10 4' 'down middle' 'up middle' 'move 20 0 2' 'up left' ;;
  titlermb) sudo ~/evseq.py $M 'down left' 'move 20 10 4' 'down right' 'move 60 30 8' 'up right' 'move 10 0 2' 'up left' ;;
  titleplain) sudo ~/evseq.py $M 'down left' 'move 40 20 4' 'up left' ;;
  plain) sudo ~/evseq.py $M 'down left' 'move 40 10 4' 'up left' ;;
esac
sleep 0.5
eval $(xdotool getwindowgeometry --shell $W)
echo "$V border@$bx,$by -> xterm ${WIDTH}x${HEIGHT} | $(~/grab-probe) | $(~/clickcheck.sh)"
