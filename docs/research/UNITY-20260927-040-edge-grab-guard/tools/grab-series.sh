#!/bin/sh
# UNITY-20260927-040 (agent A): N runs of one grab-edge.sh VARIANT, each under
# uprobetrace-040.sh. A run is STUCK when the final real click does not reach
# the sensor or a grab is still held; then the X server's grab list is logged
# (XF86LogGrabInfo, needs setxkbmap -option grab:debug) and the session is
# recovered (Escape, SIGHUP to compiz as in known issue #3, viewport 0,0).
# Output: OUTDIR/VARIANT-i.txt (trace), .result, .grabinfo; summary on stdout.
# usage: grab-series.sh VARIANT N OUTDIR
V=$1; N=$2; D=$3; mkdir -p "$D"
. ~/envt.sh
setxkbmap -option grab:debug
K=/dev/input/$(grep -l "AT Translated" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5)
stuck=0
for i in $(seq 1 "$N"); do
  sh ~/uprobetrace-040.sh "$V" "$D/$V-$i.txt"   # VP (grab-edge.sh) passes through the environment
  r=$(cat "$D/$V-$i.txt.result")
  if echo "$r" | grep -q "reached=0 " || echo "$r" | grep -q "click@.*GRABBED"; then
    stuck=$((stuck + 1)); echo "$i STUCK $r"
    n=$(sudo wc -l < /var/log/Xorg.0.log); xdotool key XF86LogGrabInfo; sleep 1
    sudo tail -n +$((n + 1)) /var/log/Xorg.0.log | sed -n '1,12p' > "$D/$V-$i.grabinfo"
    sudo ~/evkeys.py $K 'tap ESC' 'sleep 1'
    pkill -HUP -x compiz; sleep 8; xdotool set_desktop_viewport 0 0; sleep 1
    echo "$i recovered: $(~/grab-probe)"
  else
    echo "$i ok $r"
  fi
  sleep 1
done
echo "SUMMARY $V stuck $stuck/$N"
