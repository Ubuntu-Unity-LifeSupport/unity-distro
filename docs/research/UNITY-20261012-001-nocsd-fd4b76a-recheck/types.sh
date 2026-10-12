#!/bin/bash
# types.sh - the types bug (UNITY-20260927-038 claim 14) on b76f3fb and fd4b76a, on target2:
# typesorder (research/UNITY-20260927-038-nocsd-reply2-recheck/tests/typesorder.c) under gdb with trace.gdb
# (the same directory), with LD_PRELOAD of each build, with and without the early GObject (SKIP_EARLY_OBJECT=1 is
# the control). At exit gdb prints GTKNoCSDGTKWindow: 0 = the GTK types were never fetched.
set -u
B=~/b1012
export DISPLAY=:0
sp=$(pgrep -x compiz)
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
gcc -O0 -g -o $B/typesorder $B/typesorder.c $(pkg-config --cflags --libs gobject-2.0) -ldl > $B/typesorder-build.log 2>&1
echo "typesorder build rc=$?"
for c in b76f3fb fd4b76a; do
  for early in yes no; do
    if [ $early = yes ]; then skip=""; else skip="SKIP_EARLY_OBJECT=1"; fi
    # -ex before -x: trace.gdb ends with "run", and gdb runs -ex/-x in command-line order
    out=$(env $skip gdb -q -batch -ex "set environment LD_PRELOAD=$B/libgtk-nocsd-$c.so.0" -x $B/trace.gdb \
      $B/typesorder 2>&1)
    echo "== $c, early GObject $early"
    echo "$out" | grep -E "AT EXIT|GtkWindow type" | sed 's/^/  /'
    echo "  GetReferences calls: $(echo "$out" | grep -c 'GetReferences(')"
  done
done
