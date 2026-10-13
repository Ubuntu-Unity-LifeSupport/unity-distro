#!/bin/sh
# UNITY-20260927-012 (from UNITY-20260927-009; runs on builder): N restarts of target through Unity's
# dialog (restart-via-dialog.sh), each followed by usd-restart-check.sh; u-s-d crash reports
# are moved aside after each check. Usage: restart-series.sh N OUTFILE
N=${1:?}; OUT=${2:?}
settle() {
  until ssh -o ConnectTimeout=5 target 'test $(cut -d. -f1 /proc/uptime) -gt 40 && systemctl --user is-active unity7.service' 2>/dev/null | grep -qx active; do sleep 5; done
  sleep 20
}
settle
for i in $(seq 1 "$N"); do
  ssh target 'sudo systemd-run --unit=u009r-$(date +%s) sh /home/mike/restart-via-dialog.sh' >/dev/null 2>&1
  t=0; while ssh -o ConnectTimeout=5 target true 2>/dev/null && [ $t -lt 120 ]; do sleep 3; t=$((t+3)); done
  settle
  echo "restart $i: $(ssh target 'sh ~/usd-restart-check.sh')" >> "$OUT"
done
