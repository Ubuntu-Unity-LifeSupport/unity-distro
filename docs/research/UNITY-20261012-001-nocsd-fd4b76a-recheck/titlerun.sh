#!/bin/bash
# titlerun.sh - run tests/titletest.c (52fa72e / 5f5acae) on target2 in the Unity session, for b76f3fb and fd4b76a,
# modes same / differ / appname; prints the program's own readings of show-title and the title widget state.
set -u
B=~/b1012
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
for v in b76f3fb fd4b76a; do
  sudo -n cp $B/libgtk-nocsd-$v.so.0 $T.new && sudo -n mv $T.new $T
  for m in same differ appname; do
    echo "== $v $m"
    env -i "${envs[@]}" LD_PRELOAD=libgtk-nocsd.so.0 timeout 20 $B/titletest $m 2>&1 | grep -E "^(mode|t=)" | sed 's/^/  /'
  done
done
sudo -n cp $B/libgtk-nocsd.so.0.pkg $T.new && sudo -n mv $T.new $T
echo "== packaged library restored: $(sha256sum < $T | cut -c1-16)"
