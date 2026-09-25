#!/bin/bash
# epiphany under gdb in the live session; activate win.passwords's stand-in, Escape, backtrace on abort
sp=$(pgrep -x compiz | head -1)
mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
cat > /tmp/epi.gdb <<'G'
set pagination off
handle SIGPIPE nostop noprint
run
bt 25
G
env -i "${envs[@]}" gdb -q -batch -x /tmp/epi.gdb --args /usr/bin/epiphany > /tmp/epi-gdb.out 2>&1 &
sleep 20
app=$(pgrep -x epiphany | tail -1)
w=$(xdotool search --onlyvisible --pid $app | tail -1)
bus=$(xprop -id $w _GTK_UNIQUE_BUS_NAME | sed -n 's/.*= "\(.*\)"/\1/p')
wp=$(xprop -id $w _GTK_WINDOW_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
timeout 5 gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Activate gtk-nocsd-win-passwords '[]' '{}' >/dev/null 2>&1
sleep 4; xdotool key Escape; sleep 4
grep -E "^#|signal SIG|CRITICAL" /tmp/epi-gdb.out | head -30
pkill -x gdb; pkill -x epiphany
