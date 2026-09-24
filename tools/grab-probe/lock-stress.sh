#!/bin/sh
# lock-stress.sh N - lock/unlock cycles on :0, unlocking through logind, and
# check that nobody keeps a pointer/keyboard grab after the unlock.
N=${1:-40}; export DISPLAY=:0; O=$HOME/lock-stress; mkdir -p $O; L=$O/run.log
S=$(loginctl list-sessions --no-legend | awk '$3=="mike" && $4=="seat0"{print $1}')
log() { echo "$(date '+%T.%N' | cut -c1-12) $*" >> $L; }
log "start N=$N session=$S unity=$(dpkg-query -W -f='${Version}' unity)"
i=0
while [ $i -lt $N ]; do
  case $((i % 4)) in
    0) how=keys;   xdotool key ctrl+alt+l;;
    1) how=logind; sudo -n loginctl lock-session $S;;
    2) how=dash;   xdotool key super; sleep 0.7; xdotool key ctrl+alt+l;;
    3) how=hud;    xdotool key alt; sleep 0.7; sudo -n loginctl lock-session $S;;
  esac
  sleep 3; a=$(~/grab-probe)
  sudo -n loginctl unlock-session $S; sleep 3
  b=$(~/grab-probe); rc=$?
  log "$i lock=$how locked:[$a] unlocked:[$b]"
  if [ $rc -ne 0 ]; then
    xdotool key Escape; sleep 2; xdotool key Escape; sleep 2; c=$(~/grab-probe)
    if [ $? -ne 0 ]; then log "STUCK after unlock ($how): $c"; gnome-screenshot -f $O/stuck.png 2>/dev/null; exit 1; fi
    log "   transient: $c"
  fi
  i=$((i+1))
done
log "done, no stuck grab in $N lock cycles"
