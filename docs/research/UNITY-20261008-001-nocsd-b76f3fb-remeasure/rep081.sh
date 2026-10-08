#!/bin/bash
# rep081.sh N APP... - repeat the audit of a few applications N times for our series (S-on) and b76f3fb
# (U-on, U-g2), each start as in variant.sh (same breadth-any.sh, same 7 s wait), killing leftovers first.
# Results in ~/b/live/rep-<variant>.txt; the packaged library is put back at the end.
set -u
n=$1; shift
S=~/b081/nocsd-60ec176/libgtk-nocsd.so.0
U=~/b081/nocsd-b76f3fb/libgtk-nocsd.so.0
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
for v in "S-on:$S:GTK_NOCSD_GLOBAL_MENU=1" "U-on:$U:GTK_NOCSD_MENU=1" "U-g2:$U:GTK_NOCSD_MENU=1 GTK_NOCSD_MENU_GROUP=2"; do
  IFS=: read name lib extra <<<"$v"
  sudo -n cp "$lib" $T.new && sudo -n mv $T.new $T
  sed "s#setsid env -i \"\${e\[@\]}\"#setsid env -i \"\${e[@]}\" $extra#" ~/b/breadth-any.sh > /tmp/breadth-rep.sh
  : > ~/b/live/rep-$name.txt
  for i in $(seq "$n"); do
    for a in "$@"; do pkill -x "${a:0:15}"; done; sleep 2
    echo "### round $i" >> ~/b/live/rep-$name.txt
    bash /tmp/breadth-rep.sh "$@" >> ~/b/live/rep-$name.txt 2>&1
  done
done
for a in "$@"; do pkill -x "${a:0:15}"; done
sudo -n cp ~/b081/libgtk-nocsd.so.0.pkg $T.new && sudo -n mv $T.new $T
echo "packaged library restored: $(sha256sum $T | cut -c1-16)"
