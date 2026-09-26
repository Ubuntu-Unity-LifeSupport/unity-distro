#!/bin/bash
# A-2: title-bar move with a second button, fresh xterm per run. Reports final
# position, whether the window ended minimized, grabs, and whether a real click
# still reaches the sensor. Usage: title-ab.sh VARIANT N   (agent A)
. ~/envt.sh; V=$1; N=$2
for i in $(seq 1 $N); do
  pkill -x xterm; sleep 1
  r=$(NOCLICK=1 ~/resize-grab-nc.sh $V)
  W=$(xdotool search --class '^XTerm$' | tail -1)
  st=$(xprop -id $W WM_STATE 2>/dev/null | grep -oE "Iconic|Normal")
  xdotool key Escape; sleep 0.5
  echo "$V#$i unity=$(dpkg -l unity | awk '/^ii/{print $3}' | grep -oE 'unity[0-9]+$') $r state=$st | $(~/clickcheck.sh | grep -oE 'reached=[0-9]+')"
done
