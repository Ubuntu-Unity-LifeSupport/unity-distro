#!/bin/bash
# Drive N reboots of target and summarise the cursor plugin state of each.
for n in $(seq $1 $2); do
  ssh target 'sudo systemctl reboot' 2>/dev/null; sleep 25
  up=0; for i in $(seq 1 60); do ssh -o ConnectTimeout=3 target 'pgrep -x compiz >/dev/null && pgrep -f [u]nity-panel-service >/dev/null' 2>/dev/null && { up=1; break; }; sleep 5; done
  [ $up = 1 ] || { echo "a$n: session did not come up"; continue; }
  sleep 15; ssh target "~/cursor-loop.sh $3$n" 2>/dev/null
done
