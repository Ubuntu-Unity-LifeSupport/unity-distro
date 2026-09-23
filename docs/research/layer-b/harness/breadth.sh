#!/bin/bash
# breadth.sh CMD... - run each command in the real session environment (the
# installed shim comes in through LD_PRELOAD from environment.d), with the
# shim's debug log on, then audit its global menu and close it.
export DISPLAY=:0
mapfile -d '' e < /proc/$(pgrep -x compiz)/environ
export $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep '^DBUS_SESSION_BUS_ADDRESS=')
for cmd in "$@"; do
	log=/tmp/b-breadth-${cmd%% *}.log
	rm -f "$log"
	setsid env -i "${e[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG="$log" \
		$cmd >/tmp/b-breadth-${cmd%% *}.out 2>&1 < /dev/null &
	pid=$!
	sleep 7
	echo "=================== $cmd (pid $pid)"
	if ! kill -0 $pid 2>/dev/null; then
		echo "EXITED"; tail -3 /tmp/b-breadth-${cmd%% *}.out
	fi
	grep -v "hooked\|not loaded\|not Unity" "$log" 2>/dev/null | grep "\[unity-gtk4-menu $pid\]" | sed 's/^\[[^]]*\] /  shim: /' | sort | uniq
	grep -q "\[unity-gtk4-menu $pid\] hooked" "$log" 2>/dev/null || echo "  shim: NOT HOOKED in pid $pid"
	python3 ~/b/audit.py $pid | sed 's/^/  /'
	kill $pid 2>/dev/null; sleep 1; kill -9 $pid 2>/dev/null
done
