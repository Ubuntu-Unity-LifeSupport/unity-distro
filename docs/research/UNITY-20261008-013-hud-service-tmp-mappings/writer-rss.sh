#!/bin/bash
# writer-rss.sh N - UNITY-20261008-013 on target2: N Writer starts (killed in between, no HUD query), hud-service's
# VmRSS, deleted /tmp/# mappings and fds after every 5th start. A cache of imported menus levels off; a leak keeps
# growing with the starts.
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
P=$(pgrep -x hud-service | head -1)
m() { printf 'after %2s Writer starts: rss_kB %7d tmp-maps %3d fds %3d\n' "$1" "$(awk '/^VmRSS/{print $2}' /proc/$P/status)" \
  "$(grep '(deleted)' /proc/$P/maps | grep -c ' /tmp/#')" "$(ls /proc/$P/fd | wc -l)"; }
start() { local C=$(pgrep -x compiz); (cat /proc/$C/environ; printf 'setsid\0sh\0-c\0%s\0' "$1") > ~/.l13w-args
  xargs -0 -a ~/.l13w-args env -i > /dev/null 2>&1 < /dev/null & }
echo "hud $(dpkg-query -W -f='${Version}' hud), hud-service pid $P"; m 0
for i in $(seq "${1:-30}"); do
  start "libreoffice --writer --norestore"
  for j in $(seq 60); do xdotool search --onlyvisible --name "LibreOffice Writer" >/dev/null 2>&1 && break; sleep 1; done; sleep 6
  pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep 2
  [ $((i % 5)) -eq 0 ] && m $i
done
sleep 30; m "$i +30 s"
