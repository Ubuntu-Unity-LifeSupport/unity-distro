#!/bin/sh
# UNITY-20260927-040 (agent A): replay the first stuck sequence -
# grab-edge.sh "expo" (first version: expo, tablet click on the border, then
# Super+S again, which re-enters expo from viewport (1,0)) followed at once by
# grab-edge.sh "kbdresize-drag" inside that second expo, with no viewport
# reset between them (NOVP=1), both under uprobetrace-040.sh. In the original
# the check clicks landed on the launcher (0,207); MODE picks the variant:
#   orig        check clicks at 0,207 (launcher), border clicks as recorded
#   nolauncher  check clicks on the sensor instead
#   noborder    check clicks at 0,207, but the second (kbdresize-drag) click
#               80 px right of the border (grab-edge.sh BX_OFFSET)
# Then the X grab list and recovery (Escape, SIGHUP compiz, viewport 0,0).
# usage: replay-stuck1.sh OUTDIR RUN MODE
D=$1; i=$2; MODE=${3:-orig}; mkdir -p "$D"
. ~/envt.sh
setxkbmap -option grab:debug
K=/dev/input/$(grep -l "AT Translated" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5)
xdotool set_desktop_viewport 0 0; sleep 1
case $MODE in orig|noborder) export CLICKAT=0,207;; esac
NOVP=1 sh ~/uprobetrace-040.sh expo "$D/r$i-$MODE-a-expo.txt"
[ $MODE = noborder ] && export BX_OFFSET=80
NOVP=1 sh ~/uprobetrace-040.sh kbdresize-drag "$D/r$i-$MODE-b-kbdresize-drag.txt"
unset BX_OFFSET CLICKAT
echo "run $i $MODE a: $(cat "$D/r$i-$MODE-a-expo.txt.result")"
echo "run $i $MODE b: $(cat "$D/r$i-$MODE-b-kbdresize-drag.txt.result")"
echo "run $i $MODE b trace: $(grep -E '^[0-9]+ (EDGE-DOWN|PUSH-GRAB|REMOVE-GRAB|XUNGRABPOINTER|XGRABKEYBOARD)' "$D/r$i-$MODE-b-kbdresize-drag.txt" | awk '{print $2$3}' | paste -sd' ')"
n=$(sudo wc -l < /var/log/Xorg.0.log); xdotool key XF86LogGrabInfo; sleep 1
sudo tail -n +$((n + 1)) /var/log/Xorg.0.log | sed -n '1,12p' > "$D/r$i-$MODE.grabinfo"
echo "run $i $MODE active grabs: $(grep -c 'Active grab' "$D/r$i-$MODE.grabinfo") frozen: $(grep -c 'device frozen' "$D/r$i-$MODE.grabinfo")"
sudo ~/evkeys.py $K 'tap ESC' 'sleep 1'
pkill -x soffice.bin 2>/dev/null
# restart compiz only when stuck: a SIGHUP restart once took cinnamon-session
# down with it (SEGV in IceProcessMessages, runs/u12-cinnamon-session-crash.txt)
if grep -q 'device frozen' "$D/r$i-$MODE.grabinfo"; then pkill -HUP -x compiz; sleep 8; fi
xdotool set_desktop_viewport 0 0; sleep 1
echo "run $i $MODE recovered: $(~/grab-probe)"
