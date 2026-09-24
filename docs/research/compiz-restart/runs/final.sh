#!/bin/sh
# Load the new compiz, put one xterm on each lower viewport, then N SIGHUP
# restarts: positions of all terminals, bare decorations, crashes.
. ~/envt.sh
N=${1:-5}
xdotool set_desktop_viewport 0 0; sleep 1
killall -1 compiz; sleep 30
xdotool windowmove 0x3a00020 200 1000; xdotool windowmove 0x3c00020 1480 1000; sleep 2
T0=$(date +%T)
echo "before: $(~/vpdump.sh 2>/dev/null | grep 'mike@' | awk '{print $1"="$2}' | tr '\n' ' ')"
for i in $(seq 1 $N); do
  killall -1 compiz; sleep 30
  echo "restart $i: $(~/vpdump.sh 2>/dev/null | grep 'mike@' | awk '{print $1"="$2}' | tr '\n' ' ')"
done
echo "journal since $T0: $(journalctl --since $T0 --no-pager -o short-iso | grep -c -E 'segfault|general protection|core-dump|g_hash_table')"
echo "crash dir: $(ls /var/crash)"
