#!/bin/bash
# Known issue #6 (double confirmation) with real clicks: session menu ->
# "Выключить..." -> Unity's dialog -> restart button. A watcher in the guest
# records visible window names and screenshots every 0.5 s until the session
# dies, to /var/tmp/r$TAG/. Agent A.   Usage: confirm-restart.sh TAG
TAG=$1
ssh target "rm -rf /var/tmp/r$TAG; mkdir -p /var/tmp/r$TAG; cat > /var/tmp/r$TAG/w.sh <<'W'
. ~/envt.sh; k=0
while [ \$k -lt 60 ]; do
  echo \"\$(date +%T.%N | cut -c1-12) \$(xdotool search --onlyvisible --name . 2>/dev/null | while read w; do xdotool getwindowname \$w; done | sort -u | tr '\n' '|')\" >> /var/tmp/r$TAG/windows
  gnome-screenshot -f /var/tmp/r$TAG/s\$k.png 2>/dev/null; sync; k=\$((k+1)); sleep 0.5
done
W
setsid nohup bash /var/tmp/r$TAG/w.sh >/dev/null 2>&1 &"
ssh target 'T=/dev/input/$(grep -l "USB Tablet" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5); sudo ~/evclick.py $T 1253 14 left; sleep 1.5; sudo ~/evclick.py $T 1068 232 left; sleep 2.5; sudo ~/evclick.py $T 563 447 left' 2>/dev/null
sleep 30
for i in $(seq 1 60); do ssh -o ConnectTimeout=3 target 'pgrep -u mike -x compiz >/dev/null' 2>/dev/null && break; sleep 5; done
ssh target "echo \"booted \$(uptime -s)\"; ls /var/tmp/r$TAG | grep -c png; cat /var/tmp/r$TAG/windows | cut -c1-200 | tail -8"
