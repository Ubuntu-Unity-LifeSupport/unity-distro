#!/bin/bash
# rep.sh MODE LIB... - run dialogtitle MODE with each preload in the session
m=$1; shift
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
for l in "$@"; do
  out=$(env -i "${envs[@]}" LD_PRELOAD=$l timeout 10 ~/b/dialogtitle $m 2>&1); rc=$?
  echo "== $(basename $l .so) rc=$rc"; echo "$out" | grep -E "CRITICAL|dialog:|clock:" | sed 's/^.*Gtk-CRITICAL[^:]*: [0-9:.]*: /  CRITICAL /; s/^/  /'
done
