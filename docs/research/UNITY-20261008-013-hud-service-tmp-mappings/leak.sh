#!/bin/bash
# leak.sh - UNITY-20261008-013 on target2 (run as mike over ssh, in the Unity session). The same steps for every
# hud version; prints hud-service's deleted /tmp/# mappings and memory before and after each step.
#   metrics: deleted "/tmp/#" lines in /proc/PID/maps, distinct such files (inodes), VmRSS, open fds
#   1. baseline (session up, no application started by the script)
#   2. 10 HUD queries on the desktop (CreateQuery "" + CloseQuery, frequent.py)
#   3. 10 Mines starts (killed in between; no bamf move)
#   4. 10 Writer starts (killed in between; most take the bamf move, UNITY-20260929-001)
#   5. 10 HUD queries in the last Writer window
#   6. 60 s idle, then the metrics again (does anything go back?)
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
P=$(pgrep -x hud-service | head -1)
metrics() {
  local m; m=$(grep '(deleted)' /proc/$P/maps | grep ' /tmp/#')
  printf '%-34s tmp-maps %5d files %4d rss_kB %7d fds %4d\n' "$1" \
    "$(printf '%s\n' "$m" | grep -c .)" "$(printf '%s\n' "$m" | awk '{print $5}' | sort -u | grep -vc '^$')" \
    "$(awk '/^VmRSS/{print $2}' /proc/$P/status)" "$(ls /proc/$P/fd | wc -l)"
}
start() { local C=$(pgrep -x compiz); (cat /proc/$C/environ; printf 'setsid\0sh\0-c\0%s\0' "$1") > ~/.l13-args
  xargs -0 -a ~/.l13-args env -i > /dev/null 2>&1 < /dev/null & }
queries() { for i in $(seq 10); do python3 ~/b013/frequent.py > /dev/null 2>&1; done; }
echo "hud $(dpkg-query -W -f='${Version}' hud), hud-service pid $P, up $(ps -o etime= -p $P)"
metrics "1 baseline"
queries; metrics "2 after 10 queries (desktop)"
for i in $(seq 10); do start gnome-mines; sleep 6; pkill -x gnome-mines; sleep 2; done
metrics "3 after 10 Mines starts"
for i in $(seq 10); do start "libreoffice --writer --norestore"
  for j in $(seq 60); do xdotool search --onlyvisible --name "LibreOffice Writer" >/dev/null 2>&1 && break; sleep 1; done; sleep 6
  [ $i -lt 10 ] && { pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep 2; }; done
metrics "4 after 10 Writer starts"
w=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1); xdotool windowactivate --sync $w; sleep 1
queries; metrics "5 after 10 queries (Writer)"
pkill -x soffice.bin; sleep 60; metrics "6 Writer closed, 60 s idle"
