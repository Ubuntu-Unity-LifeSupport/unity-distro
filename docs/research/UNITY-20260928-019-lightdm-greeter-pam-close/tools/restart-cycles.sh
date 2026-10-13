#!/bin/sh
# UNITY-20260928-019: does a *user* session's session-child finish its
# cleanup (utmp/wtmp DEAD_PROCESS, audit logout, X authority, PAM close) when
# the daemon stops it? N times: restart lightdm while a seat0 user session
# runs (after the first restart: mike's autologin), then look at the journal
# of that session-child and at the utmp/wtmp records for display :0.
# session-child writes USER_PROCESS with ut_id ":0" at start and DEAD_PROCESS
# (ut_pid 0, same ut_id) after waitpid() - only wtmp on resolute, which has no
# utmp file; the no-child branch of signal_cb()
# skips the second. Run as root. Usage: restart-cycles.sh N
set -u
N=${1:?cycles}
for c in $(seq 1 "$N"); do
  i=0; until loginctl list-sessions --no-legend | awk '$4=="seat0" && $6=="user"' | grep -q . || [ $i -ge 120 ]; do sleep 1; i=$((i+1)); done
  sleep 30
  set -- $(loginctl list-sessions --no-legend | awk '$4=="seat0" && $6=="user" {print $3, $5}')
  u=$1; pid=$2
  start=$(date +%s)
  echo "cycle $c: $u's session leader (session-child) $pid; restarting lightdm"
  systemctl restart lightdm
  sleep 5
  echo "  journal lightdm[$pid] 'session closed for user $u': $(journalctl -q --since "@$start" _PID=$pid -g "session closed for user $u" | wc -l)"
  echo "  wtmp after restart (last 3):"; python3 /home/mike/wtmp-tail.py 3 | sed "s/^/    /"
done
