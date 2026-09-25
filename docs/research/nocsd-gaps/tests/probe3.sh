#!/bin/bash
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
for a in gnome-disks gnome-connections gnome-taquin gnome-tetravex four-in-a-row five-or-more hitori gnome-klotski dconf-editor seahorse; do
  env -i "${envs[@]}" GTK_MODULES=$HOME/b/libprobe3.so $a > /tmp/p3-$a.out 2>&1 & p=$!
  sleep 9; grep -E "PROBE3S|PROBE3A NOT|PROBE3A noaction" /tmp/p3-$a.out || echo "PROBE3 $a nothing"; kill $p 2>/dev/null; sleep 1; kill -9 $p 2>/dev/null
done
