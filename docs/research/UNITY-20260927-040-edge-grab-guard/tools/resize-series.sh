#!/bin/bash
# Run resize-grab.sh VARIANT N times from a clean state; on a stuck grab, record
# the X server's grab info and the grab window, then recover with the release
# notes' workaround (killall -1 compiz). Agent A, known issue #3.
. ~/envt.sh; V=$1; N=${2:-5}; mkdir -p ~/rg
recover() { local k; killall -1 compiz; for k in $(seq 1 40); do sleep 1; pgrep -x compiz >/dev/null && ~/grab-probe | grep -q "pointer=free" && break; done; sleep 6; }
for i in $(seq 1 $N); do
  r=$(~/resize-grab.sh $V)
  if echo "$r" | grep -q "reached=0"; then
    n=$(wc -l < /var/log/Xorg.0.log); setxkbmap -option grab:debug; xdotool key XF86LogGrabInfo; sleep 0.5
    sed -n "$((n+1)),\$p" /var/log/Xorg.0.log | sed -n '/active device grabs/,/End list of active/p' > ~/rg/$V-$i.grab
    g=$(grep -oE "Active grab 0x[0-9a-f]+" ~/rg/$V-$i.grab | head -1 | awk '{print $3}')
    info="grabwin=$g $(xwininfo -id $g 2>/dev/null | grep -oE 'Window id: 0x[0-9a-f]+ "[^"]*"|Width: [0-9]+|Height: [0-9]+' | tr '\n' ' ') parent=$(xwininfo -children -id $g 2>/dev/null | grep -oE 'Parent window id: 0x[0-9a-f]+ [^ ]*' ) $(grep -oE 'client pid [0-9]+ [^ ]+|device frozen, state [0-9]+|passive grab type [0-9]+, detail 0x[0-9a-f]+' ~/rg/$V-$i.grab | tr '\n' ' ')"
    setxkbmap -option ""; setxkbmap -layout us,ua -option grp:alt_shift_toggle
    recover; echo "$V#$i STUCK | $r | $info | after recover: $(~/clickcheck.sh)"
  else echo "$V#$i ok | $r"; fi
done
