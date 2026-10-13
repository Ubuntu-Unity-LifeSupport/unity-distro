#!/bin/sh
# UNITY-20260927-010 (runs on builder): N cold logins = reboots with
# autologin; after each, wait 200 s after sshd is up (no ssh login before
# that) and run login-check.sh.
# Usage: boot-series.sh N OUTFILE
N=${1:?}; OUT=${2:?}
for i in $(seq 1 "$N"); do
  ssh target 'sudo systemctl reboot' >/dev/null 2>&1
  t=0; while ssh -o ConnectTimeout=5 target true 2>/dev/null && [ $t -lt 120 ]; do sleep 3; t=$((t+3)); done
  # wait for sshd without logging in: an ssh login as mike would start his
  # user manager before the graphical login and change what is measured
  until timeout 3 bash -c 'exec 3<>/dev/tcp/192.168.56.20/22' 2>/dev/null; do sleep 3; done
  sleep 200
  echo "login $i: $(ssh target 'sudo sh /home/mike/login-check.sh')" >> "$OUT"
done
