#!/bin/bash
# respond.sh PRELOAD CMD APPID APPPATH - seconds until the app answers org.gtk.Actions.DescribeAll
export DISPLAY=:0
mapfile -d '' e < /proc/$(pgrep -x compiz)/environ
for i in "${!e[@]}"; do [[ ${e[$i]} == LD_PRELOAD=* ]] && e[$i]="LD_PRELOAD=$1"; done
export $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep '^DBUS_SESSION_BUS_ADDRESS=')
setsid env -i "${e[@]}" $2 >/dev/null 2>&1 </dev/null & pid=$!
t0=$(date +%s.%N); first=""; fails=0
for n in $(seq 1 40); do
	if timeout 1 gdbus call --session -d $3 -o $4 -m org.gtk.Actions.DescribeAll >/dev/null 2>&1; then
		[ -z "$first" ] && first=$(echo "$(date +%s.%N) - $t0" | bc)
	elif [ -n "$first" ]; then fails=$((fails+1)); fi
	sleep 0.5
done
echo "preload=[$1] first answer after ${first:-never} s, failures after that: $fails"
if [ "$fails" -gt 10 ]; then
	echo "STUCK pid $pid kept alive"; for t in /proc/$pid/task/*; do echo "  $(cat $t/comm) state=$(awk '{print $3}' $t/stat) wchan=$(cat $t/wchan)"; done
	exit 2
fi
kill $pid 2>/dev/null; sleep 1; kill -9 $pid 2>/dev/null
exit 0
