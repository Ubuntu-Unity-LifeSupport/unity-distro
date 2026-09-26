#!/bin/bash
# dt.sh - restart indicator-datetime-service in the session with core dumps; report after 15 s
sudo -n sysctl -q kernel.core_pattern=/tmp/core.%e.%p
rm -f /tmp/core.indicator-datet*
n0=$(sudo -n dmesg | grep -c "indicator-datet")
systemctl --user stop indicator-datetime.service 2>/dev/null
pkill -x indicator-datet; sleep 1
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
bash -c 'ulimit -c unlimited; exec env -i "$@" G_MESSAGES_DEBUG= /usr/lib/x86_64-linux-gnu/indicator-datetime/indicator-datetime-service' _ "${envs[@]}" > /tmp/dt.out 2>&1 &
p=$!
sleep ${WAIT:-15}
if [ -d /proc/$p ]; then echo "service alive"; else wait $p; echo "service DEAD rc=$?"; fi
ls /tmp/core.indicator-datet* 2>/dev/null
grep -E "CRITICAL|WARNING|assertion|ERROR" /tmp/dt.out | cut -c1-200 | sort | uniq -c | head -8
kill $p 2>/dev/null
