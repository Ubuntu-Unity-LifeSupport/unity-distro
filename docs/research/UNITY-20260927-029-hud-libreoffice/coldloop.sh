#!/bin/bash
# coldloop.sh N - reboot target2 N times; after each boot, wait for the session's hud-service and
# window-stack-bridge, then one Writer start with lo7.sh (the first LibreOffice start after login)
for b in $(seq $1); do
  ssh target2 'sudo -n systemctl reboot' 2>/dev/null
  sleep 40
  until ssh -o ConnectTimeout=5 -o BatchMode=yes target2 'pgrep -x hud-service >/dev/null && pgrep -x window-stack-br >/dev/null' 2>/dev/null; do sleep 5; done
  sleep 20
  echo "boot $b: $(ssh target2 'GAP=0 WATCH_DELAY=0 bash ~/b029/lo7.sh 1 2>&1 | tail -1')"
done
