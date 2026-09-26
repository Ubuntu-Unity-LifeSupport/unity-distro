#!/bin/bash
# Known issue #2 (menu dead after cancelling) with real clicks (tablet evdev):
# open the session menu, choose an item, check Unity's dialog is drawn
# (screenshot pixel on the right button), cancel it (close cross or Escape),
# check it is gone. Usage: dlg-cycles.sh N ITEM_Y CANCEL(cross|esc)   Agent A.
N=$1; IY=$2; C=$3; CX=${4:-460}; CY=${5:-238}; S=/tmp/claude-1000/-home-claude/dcdcb403-a4d1-44d1-ae1e-afc145fa20ae/scratchpad/dlg
mkdir -p $S; t() { ssh target "$@"; }
click() { t 'T=/dev/input/$(grep -l "USB Tablet" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5); sudo ~/evclick.py $T '"$1 $2"' left'; }
shot() { t '. ~/envt.sh; gnome-screenshot -f /tmp/d.png 2>/dev/null'; scp -q target:/tmp/d.png $S/$1.png; convert $S/$1.png -format '%[fx:int(255*p{680,410}.r)],%[fx:int(255*p{680,410}.g)],%[fx:int(255*p{680,410}.b)]' info:; }
isdlg() { r=${1%%,*}; [ "$r" -gt 150 ] && echo yes || echo no; }
for i in $(seq 1 $N); do
  click 1253 14; sleep 1.5; click 1068 $IY; sleep 2.5
  a=$(shot c$i-open)
  if [ $C = esc ]; then t '. ~/envt.sh; xdotool key Escape'; else click $CX $CY; fi; sleep 2
  b=$(shot c$i-cancel)
  echo "cycle $i: dialog after choose=$(isdlg $a) ($a) | after cancel=$(isdlg $b) ($b)"
done
