#!/bin/bash
# keyprep.sh TAG CLASS APP [ARGS...] - on target2 in the Unity session: start APP with UNITY-20261012-003's start.sh
# (NOAUDIT=1: the panel and hud-service are the only menu subscribers), activate its window by WM_CLASS, check that it
# is the active window, print the panel's entry table (sync.sh), then start popwatch.sh for 20 s. The key then comes
# from the host (vbox send_keys) and Escape a few seconds later; /tmp/pop-TAG.txt holds the popup events.
set -u
tag=$1; class=$2; shift 2
B=~/b1203
export $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep -E '^XAUTHORITY=') DISPLAY=:0
NOAUDIT=1 bash $B/start.sh "$tag" "$@" 2>&1 | grep -E '^==|_GTK_MENUBAR|ready' | sed 's/^/  /'
w=$(xdotool search --onlyvisible --class "$class" | tail -1)
xdotool windowactivate --sync "$w" 2>/dev/null; sleep 0.5
echo "  window $w, active $(xdotool getactivewindow)"
bash $B/sync.sh "$tag" | grep -E "win=$w" | sed 's/^/  /'
nohup bash $B/popwatch.sh 20 > /tmp/pop-$tag.txt 2>&1 < /dev/null &
sleep 0.6; echo "  popwatch: $(head -1 /tmp/pop-$tag.txt)"
