#!/bin/sh
# grab-stress.sh N [SEED] - drive Unity through N random UI actions on :0 and
# check after each one that nobody is left holding a pointer or keyboard grab.
# Stops at the first stuck grab and asks the X server to log who holds it
# (XF86LogGrabInfo, enabled with setxkbmap -option grab:debug).
# Needs xdotool and grab-probe next to this script. Log: ~/grab-stress/run.log
N=${1:-100}; SEED=${2:-$$}
export DISPLAY=:0
D=$(dirname "$0"); O=$HOME/grab-stress; mkdir -p $O; L=$O/run.log
setxkbmap -option grab:debug
pgrep -x xterm >/dev/null || { xterm -geometry 80x20+300+200 & sleep 2; }
log() { echo "$(date '+%T.%N' | cut -c1-12) $*" >> $L; }
awk_rand() { awk -v s="$SEED" -v i="$1" -v n="$2" 'BEGIN{srand(s*1000+i); print int(rand()*n)}'; }
actions="dash hud alttab spread expo power menu drag dash_power hud_alttab menu_escape_fast power_escape_fast"
set -- $actions; NA=$#
log "start N=$N seed=$SEED boot=$(uptime -s) unity=$(dpkg-query -W -f='${Version}' unity) compiz=$(dpkg-query -W -f='${Version}' compiz-core)"
i=0
while [ $i -lt $N ]; do
  k=$(awk_rand $i $NA); j=0; for a in $actions; do [ $j -eq $k ] && act=$a; j=$((j+1)); done
  case $act in
    dash)   xdotool key super; sleep 1; xdotool key Escape;;
    hud)    xdotool key alt; sleep 1; xdotool key Escape;;
    alttab) xdotool keydown alt key Tab; sleep 0.5; xdotool key Tab; xdotool keyup alt;;
    spread) xdotool key super+w; sleep 1; xdotool key Escape;;
    expo)   xdotool key super+s; sleep 1; xdotool key Escape;;
    power)  xdotool key XF86PowerOff; sleep 1.5; xdotool key Escape;;
    menu)   xdotool mousemove 1253 14 click 1; sleep 1; xdotool key Escape;;
    drag)   xdotool mousemove 500 212 mousedown 1; sleep 0.2; xdotool mousemove 600 300; sleep 0.2; xdotool mouseup 1;;
    dash_power) xdotool key super; sleep 0.5; xdotool key XF86PowerOff; sleep 1.5; xdotool key Escape; sleep 0.3; xdotool key Escape;;
    hud_alttab) xdotool key alt; sleep 0.5; xdotool keydown alt key Tab; sleep 0.3; xdotool keyup alt; sleep 0.5; xdotool key Escape;;
    menu_escape_fast) xdotool mousemove 1253 14 click 1 key Escape;;
    power_escape_fast) xdotool key XF86PowerOff key Escape;;
  esac
  sleep 2
  r=$($D/grab-probe); rc=$?
  log "$i $act -> $r"
  if [ $rc -ne 0 ]; then
    # A dialog that opened after our Escape holds a legitimate grab. Stuck
    # means the grab survives two more Escapes.
    sleep 2; xdotool key Escape; sleep 2; xdotool key Escape; sleep 2
    r2=$($D/grab-probe)
    if [ $? -ne 0 ]; then
      log "STUCK after $act: $r2"
      xdotool key XF86LogGrabInfo; sleep 1
      sudo -n tail -60 /var/log/Xorg.0.log > $O/xorg-grabinfo.log 2>/dev/null
      gnome-screenshot -f $O/stuck.png 2>/dev/null
      exit 1
    fi
    log "   transient, free again: $r2"
  fi
  i=$((i+1))
done
log "done, no stuck grab in $N actions"
