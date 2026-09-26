#!/bin/bash
# ik.sh ACTION - run indicator-keyboard-service as lightdm in the greeter's bus, then ACTION; report
sudo -n sysctl -q kernel.core_pattern=/tmp/core.%e.%p
sudo -n pkill -u lightdm -f [i]ndicator-keyboard-service
sudo -n rm -f /tmp/core.indicator*
sudo -n -u lightdm bash -c 'ulimit -c unlimited; cd /tmp; exec env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/109/bus XDG_RUNTIME_DIR=/run/user/109 DISPLAY=:0 G_MESSAGES_DEBUG=all /usr/libexec/indicator-keyboard/indicator-keyboard-service' > /tmp/ik.out 2>&1 &
sleep 6
p=$(pgrep -u lightdm -x indicator-keybo); echo "service pid $p"
eval "$1"
sleep 8
if [ -n "$p" ] && [ -d /proc/$p ]; then echo "ACTION '$1': service alive"; else echo "ACTION '$1': service DEAD"; fi
ls /tmp/core.indicator* 2>/dev/null
grep -E "CRITICAL|WARNING|Segmentation" /tmp/ik.out | head -5
