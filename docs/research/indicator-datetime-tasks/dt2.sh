#!/bin/bash
# dt2.sh - start the service, change timezone and date under it, report
sudo -n sysctl -q kernel.core_pattern=/tmp/core.%e.%p
rm -f /tmp/core.indicator-datet*
systemctl --user stop indicator-datetime.service 2>/dev/null; pkill -x indicator-datet; sleep 1
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
bash -c 'ulimit -c unlimited; exec env -i "$@" /usr/lib/x86_64-linux-gnu/indicator-datetime/indicator-datetime-service' _ "${envs[@]}" > /tmp/dt.out 2>&1 &
p=$!; sleep 8
tz0=$(timedatectl show -p Timezone --value)
for z in America/New_York Asia/Kolkata Pacific/Chatham Australia/Lord_Howe $tz0; do sudo -n timedatectl set-timezone $z; sleep 3; [ -d /proc/$p ] || { echo "DEAD after TZ $z"; break; }; done
sudo -n timedatectl set-ntp false
now=$(date +%s)
for d in "+1 day" "+40 days" "-1 day"; do sudo -n date -s "@$(( now + $(date -d "1970-01-01 UTC $d" +%s) ))" >/dev/null; sleep 4; [ -d /proc/$p ] || { echo "DEAD after date $d"; break; }; done
sudo -n date -s "@$(( now + 25 ))" >/dev/null; sudo -n timedatectl set-ntp true
sleep 3
if [ -d /proc/$p ]; then echo "service alive after TZ and date changes"; else wait $p; echo "service DEAD rc=$?"; fi
ls /tmp/core.indicator-datet* 2>/dev/null
grep -E "CRITICAL|assertion|ERROR" /tmp/dt.out | cut -c1-200 | sort | uniq -c | head -5
gdbus call --session -d com.canonical.indicator.datetime -o /com/canonical/indicator/datetime/desktop -m org.gtk.Menus.Start '[0,1]' 2>&1 | grep -o "label': <'[^']*'" | head -12
kill $p
