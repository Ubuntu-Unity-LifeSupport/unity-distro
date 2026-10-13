#!/bin/sh
# UNITY-20260927-004: N rounds of "log utest out, then exit-alloc-once.sh".
# Usage: exit-alloc-loop.sh N PASSWORD OUTDIR
set -u
N=${1:?rounds}; PW=${2:?password}; D=${3:?outdir}
for r in $(seq 1 "$N"); do
  setpriv --reuid=utest --regid=utest --init-groups env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus \
    gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager \
    --method org.gnome.SessionManager.Logout 1 >/dev/null
  i=0; until pgrep -x lightdm-gtk-gre >/dev/null || [ $i -ge 60 ]; do sleep 1; i=$((i+1)); done
  sleep 8
  sh /home/mike/exit-alloc-once.sh "$PW" "$D/round$r"
  sleep 20
done
