#!/bin/sh
# N SIGHUP restarts of compiz; after each: decoration state of the terminal
# windows, their positions, crashes and criticals.
. ~/envt.sh
N=${1:-5}
T0=$(date +%T)
ls /var/crash
for i in $(seq 1 $N); do
  pid=$(pgrep -x compiz)
  killall -1 compiz
  sleep 30
  bare=$(python3 ~/decostate.py 2>/dev/null | grep "mike@" | grep -c "shadow_rect=(0, 0, 0, 0)")
  total=$(python3 ~/decostate.py 2>/dev/null | grep -c "mike@")
  pos=$(~/vpdump.sh 2>/dev/null | grep "mike@" | awk '{print $2}' | tr '\n' ' ')
  echo "restart $i: pid $pid -> $(pgrep -x compiz), terminals $total, bare $bare, $pos"
done
gnome-screenshot -f /tmp/hup-final.png 2>/dev/null
echo "journal since $T0:"
journalctl --since $T0 --no-pager -o short-iso | grep -E "segfault|general protection|core-dump|SEGV|g_hash_table|CRITICAL" | sort | uniq -c | head
echo "crash dir: $(ls /var/crash)"
