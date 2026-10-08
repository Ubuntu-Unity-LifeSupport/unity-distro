#!/bin/bash
# coldloop4.sh N OUTDIR - UNITY-20260929-002 round 3: reboot target2 N times; after each boot wait for
# hud-service and window-stack-bridge, record their start times, then start Writer (as lo7.sh does) under a
# dbus-monitor capture, and run livequery.py as soon as the Writer window is visible (no extra wait), so the
# query lands inside hud-service's import of the menu when the import is slow. Per boot: OUTDIR/boot-N.txt
# (livequery output, unique names, service start times) and OUTDIR/boot-N.raw (the capture).
set -u
n=${1:-10}; out=${2:?outdir}; mkdir -p "$out"
for b in $(seq "$n"); do
  ssh target2 'sudo -n systemctl reboot' 2>/dev/null
  sleep 40
  until ssh -o ConnectTimeout=5 -o BatchMode=yes target2 'pgrep -x hud-service >/dev/null && pgrep -x window-stack-br >/dev/null' 2>/dev/null; do sleep 5; done
  sleep 20
  ssh target2 'bash -s' > "$out/boot-$b.txt" 2>&1 <<'EOS'
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
echo "# boot $(cat /proc/sys/kernel/random/boot_id) uptime $(cut -d' ' -f1 /proc/uptime) $(date -u +%FT%TZ)"
echo "# hud-service started $(ps -o lstart= -p $(pgrep -x hud-service)); window-stack-bridge $(ps -o lstart= -p $(pgrep -x window-stack-br))"
pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep 2
dbus-monitor --session "interface='org.gtk.Menus'" "interface='com.canonical.Unity.WindowStack'" "interface='com.canonical.hud'" "interface='com.canonical.hud.query'" > ~/b029/lq.raw 2>&1 &
mon=$!
sleep 1
P=$(pgrep -x compiz)
(cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "libreoffice --writer --norestore") > ~/.ht-args
echo "# $(date +%s.%N | cut -c1-14) START libreoffice --writer"
xargs -0 -a ~/.ht-args env -i > ~/app-lo.log 2>&1 < /dev/null &
i=0; while ! xdotool search --onlyvisible --name "LibreOffice Writer" >/dev/null 2>&1 && [ $i -lt 600 ]; do sleep 0.1; i=$((i+1)); done
w=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1)
echo "# $(date +%s.%N | cut -c1-14) VISIBLE xid $w"
xdotool windowactivate --sync "$w"
echo "# $(date +%s.%N | cut -c1-14) QUERY"
python3 ~/b029/livequery.py "Сохранить" ~/b029/lq.txt
cat ~/b029/lq.txt
kill $mon
echo "## window stack"
gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack 2>&1 | cut -c1-300
EOS
  scp -q target2:b029/lq.raw "$out/boot-$b.raw" 2>/dev/null
  echo "boot $b: $(grep -E 'legacy|\+0s|\+2s|\+5s|\+10s|\+20s' "$out/boot-$b.txt" | sed 's/^ *//' | tr '\n' ' ')"
done
