#!/bin/bash
# #2 with finer evidence: after opening the session menu (menu drawn?), after
# choosing the item (dialog drawn?), the session bus call EndSessionDialog.Open
# (did the indicator ask?), after cancel (dialog gone?). Real clicks. Agent A.
# Usage: dlg-cycles2.sh N ITEM_Y (esc cancel)
N=$1; IY=$2; S=/tmp/claude-1000/-home-claude/dcdcb403-a4d1-44d1-ae1e-afc145fa20ae/scratchpad/dlg2; mkdir -p $S
t() { ssh target "$@"; }
click() { t 'T=/dev/input/$(grep -l "USB Tablet" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5); sudo ~/evclick.py $T '"$1 $2"' left'; }
px() { t '. ~/envt.sh; gnome-screenshot -f /tmp/d.png 2>/dev/null'; scp -q target:/tmp/d.png $S/$1.png; convert $S/$1.png -format "%[fx:int(255*p{$2,$3}.r)]" info:; }
t '~/esd-mon.sh'; sleep 1
for i in $(seq 1 $N); do
  n0=$(t 'grep -c "member=Open" /tmp/esd.log')
  click 1253 14; sleep 1.5; m=$(px m$i 1100 190)
  click 1068 $IY; sleep 2.5; d=$(px d$i 680 410)
  n1=$(t 'grep -c "member=Open" /tmp/esd.log')
  t '. ~/envt.sh; xdotool key Escape'; sleep 2; c=$(px c$i 680 410)
  echo "cycle $i: menu=$([ $m -lt 60 ] && echo yes || echo no)($m) Open-calls=+$((n1-n0)) dialog=$([ $d -gt 150 ] && echo yes || echo no)($d) after-cancel=$([ $c -gt 150 ] && echo yes || echo no)"
done
