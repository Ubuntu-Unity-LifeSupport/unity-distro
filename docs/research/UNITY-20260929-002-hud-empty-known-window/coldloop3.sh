#!/bin/bash
# coldloop3.sh N OUTDIR - UNITY-20260929-002 root-cause loop: reboot target2 N times; after each boot wait for
# the session's hud-service and window-stack-bridge, then one Writer start under menutrace.sh (the D-Bus order
# of WindowCreated, hud-service's org.gtk.Menus Start and the application's Changed signals, then one HUD
# query), then lowindows.sh (every LibreOffice window, the focus, the window stack, a second HUD query).
# Per boot: OUTDIR/boot-N.txt (summary), OUTDIR/boot-N.raw (the whole dbus-monitor capture).
set -u
n=${1:-10}; out=${2:?outdir}; mkdir -p "$out"
for b in $(seq "$n"); do
  ssh target2 'sudo -n systemctl reboot' 2>/dev/null
  sleep 40
  until ssh -o ConnectTimeout=5 -o BatchMode=yes target2 'pgrep -x hud-service >/dev/null && pgrep -x window-stack-br >/dev/null' 2>/dev/null; do sleep 5; done
  sleep 20
  ssh target2 'bash ~/b029/menutrace.sh ~/b029/mt.txt >/dev/null 2>&1; sh ~/b029/lowindows.sh > ~/b029/lw.txt 2>&1'
  {
    echo "# boot $b $(date -u +%FT%TZ)"
    ssh target2 'cat ~/b029/mt.txt; echo "## lowindows"; cat ~/b029/lw.txt'
    echo "## journal since boot: hud-service, window-stack-bridge, bamfdaemon, bamf activation"
    ssh target2 'journalctl --user -b --no-pager -o short-precise 2>/dev/null | grep -E "hud-service|window-stack-bridge|bamfdaemon|org\.ayatana\.bamf|unity-panel-service" | grep -v -E "Started|Starting|Reached" | tail -40'
  } > "$out/boot-$b.txt" 2>&1
  scp -q target2:b029/mt.txt.raw "$out/boot-$b.raw" 2>/dev/null
  echo "boot $b: $(grep -E 'HUD answered' "$out/boot-$b.txt" | head -1) / second query: $(sed -n '/HUD query for the focused/{n;p}' "$out/boot-$b.txt")"
done
