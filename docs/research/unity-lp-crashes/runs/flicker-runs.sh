#!/bin/sh
# Run shaped-flicker N times; count compiz crashes (pid change or crash file).
. ~/envt.sh
for r in $(seq 1 ${1:-2}); do
  C=$(pgrep -x compiz); T=$(date +%T)
  timeout 60 ~/shaped-flicker 200 >/dev/null 2>&1
  sleep 20
  echo "run $r: compiz $C -> $(pgrep -x compiz); crash files: $(ls /var/crash | tr '\n' ' '); segv in journal: $(journalctl --since $T --no-pager | grep -c 'compiz.*segfault\|unity7.service: Main process exited, code=dumped')"
  mkdir -p ~/crash-keep/flicker-$r; mv /var/crash/*.crash ~/crash-keep/flicker-$r/ 2>/dev/null
  sleep 15
done
