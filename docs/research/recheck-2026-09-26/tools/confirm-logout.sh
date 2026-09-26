#!/bin/bash
# Known issue #6 on the logout path: session menu -> "Завершить сеанс..." ->
# Unity's dialog -> "Выйти из системы" (real clicks). Watcher records visible
# windows every 0.5 s; then: did the session end and the greeter come up,
# and was there any second dialog? Back in via a lightdm restart. Agent A.
TAG=$1
ssh target "rm -rf /var/tmp/l$TAG; mkdir -p /var/tmp/l$TAG; cat > /var/tmp/l$TAG/w.sh <<'W'
. ~/envt.sh; k=0
while [ \$k -lt 40 ] && pgrep -u mike -x compiz >/dev/null; do
  echo \"\$(date +%T.%N | cut -c1-12) \$(xdotool search --onlyvisible --name . 2>/dev/null | while read w; do xdotool getwindowname \$w; done | sort -u | tr '\n' '|')\" >> /var/tmp/l$TAG/windows; k=\$((k+1)); sleep 0.5
done; echo \"\$(date +%T) watcher end k=\$k\" >> /var/tmp/l$TAG/windows
W
setsid nohup bash /var/tmp/l$TAG/w.sh >/dev/null 2>&1 < /dev/null &"
ssh target 'T=/dev/input/$(grep -l "USB Tablet" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5); sudo ~/evclick.py $T 1253 14 left; sleep 1.5; sudo ~/evclick.py $T 1086 180 left; sleep 2.5; sudo ~/evclick.py $T 728 458 left'
sleep 20
ssh target "echo \"compiz(mike)=\$(pgrep -u mike -xc compiz) greeter=\$(pgrep -xc lightdm-gtk-gre) seat0=\$(loginctl list-sessions --no-legend | awk '\$4==\"seat0\"{print \$3}')\"; grep -cE 'Выключить систему|Завершить сеанс\?|End Session|Log Out' /var/tmp/l$TAG/windows; tail -3 /var/tmp/l$TAG/windows | cut -c1-180; sudo systemctl restart lightdm"
for i in $(seq 1 60); do ssh target 'pgrep -u mike -x compiz >/dev/null && pgrep -f [u]nity-panel-service >/dev/null' 2>/dev/null && break; sleep 3; done; sleep 20
