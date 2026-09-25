#!/bin/bash
# activate.sh CMD WAIT ACTION... - start CMD in the session, then activate
# each window action over D-Bus the way a global menu does; list new windows
cmd=$1; wait=$2; shift 2
sp=$(pgrep -x ${SESSPROC:-compiz} | head -1)
mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
env -i "${envs[@]}" $cmd > /tmp/act.out 2>&1 & app=$!
sleep $wait
w=$(xdotool search --onlyvisible --pid $app 2>/dev/null | tail -1)
bus=$(xprop -id $w _GTK_UNIQUE_BUS_NAME | sed -n 's/.*= "\(.*\)"/\1/p')
wp=$(xprop -id $w _GTK_WINDOW_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
for a in "$@"; do
	before=$(xdotool search --onlyvisible --pid $app 2>/dev/null | wc -l)
	r=$(gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Activate "$a" '[]' '{}' 2>&1 | head -1)
	sleep 3
	names=$(for x in $(xdotool search --onlyvisible --pid $app 2>/dev/null); do xdotool getwindowname $x; done | sort -u | tr '\n' '|')
	echo "$a -> ${r} windows $before->$(xdotool search --onlyvisible --pid $app 2>/dev/null | wc -l) [$names]"
	xdotool key Escape; sleep 1
done
kill $app 2>/dev/null
