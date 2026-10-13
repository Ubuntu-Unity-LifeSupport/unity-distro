#!/bin/bash
# rss-queries.sh N - UNITY-20261008-013 on target2: N more empty HUD queries (frequent.py), hud-service's VmRSS and
# deleted mappings every 10. Without the leak RSS should level off (caches) instead of growing by ~0.4 MB per query.
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
P=$(pgrep -x hud-service | head -1)
m() { printf 'after %3s more queries: rss_kB %7d deleted-maps %3d\n' "$1" "$(awk '/^VmRSS/{print $2}' /proc/$P/status)" \
  "$(grep -c '(deleted)$' /proc/$P/maps)"; }
m 0
for i in $(seq "${1:-50}"); do python3 ~/b013/frequent.py > /dev/null 2>&1; [ $((i % 10)) -eq 0 ] && m $i; done
