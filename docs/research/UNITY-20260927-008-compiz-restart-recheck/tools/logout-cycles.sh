#!/bin/sh
# UNITY-20260927-008: N cycles of "log mike out through the session manager,
# greeter, restart lightdm for autologin", run by root through systemd-run
# so that mike has no session but the graphical one (as research/compiz-restart
# lo-root.sh). Then: segfaults / core dumps in the journal, /var/crash.
# Usage: logout-cycles.sh N OUTFILE
set -u
N=${1:?cycles}; OUT=${2:?outfile}
T0=$(date '+%F %T')
for c in $(seq 1 "$N"); do
  i=0; until loginctl list-sessions --no-legend | awk '$3=="mike" && $4=="seat0"' | grep -q . || [ $i -ge 120 ]; do sleep 1; i=$((i+1)); done
  sleep 45
  C=$(pgrep -x compiz)
  echo "cycle $c: compiz $C, logging out" >> "$OUT"
  setpriv --reuid=mike --regid=mike --init-groups env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
    gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager \
    --method org.gnome.SessionManager.Logout 1 >/dev/null 2>&1
  i=0; until pgrep -x lightdm-gtk-gre >/dev/null || [ $i -ge 90 ]; do sleep 1; i=$((i+1)); done
  echo "cycle $c: greeter after ${i}s; compiz $C gone: $(kill -0 $C 2>/dev/null && echo no || echo yes)" >> "$OUT"
  journalctl _PID=$C --no-pager -o short-iso | tail -3 >> "$OUT"
  sleep 5
  systemctl restart lightdm
done
i=0; until loginctl list-sessions --no-legend | awk '$3=="mike" && $4=="seat0"' | grep -q . || [ $i -ge 120 ]; do sleep 1; i=$((i+1)); done
sleep 30
echo "journal since $T0: segfault|general protection|dumped core|g_hash_table: $(journalctl --since "$T0" --no-pager | grep -c -E 'segfault|general protection|dumped core|core-dump|g_hash_table')" >> "$OUT"
echo "/var/crash: $(ls /var/crash | tr '\n' ' ')" >> "$OUT"
