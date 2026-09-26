#!/bin/bash
# epigdb2.sh LIB [fatal] - epiphany under gdb with LD_PRELOAD=LIB, click Passwords, backtrace
lib=$1
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
pkill -9 -x epiphany; sleep 1
cat > /tmp/e2.gdb <<G
set pagination off
handle SIGPIPE nostop noprint
handle SIGTRAP nostop noprint nopass
set disable-randomization off
set environment LD_PRELOAD $lib
${2:+set environment G_DEBUG fatal-criticals}
run
bt 14
frame 1
info locals
G
env -i "${envs[@]}" gdb -q -batch -x /tmp/e2.gdb --args /usr/bin/epiphany > /tmp/e2.out 2>&1 &
sleep 20
w=$(xdotool search --onlyvisible --classname epiphany | tail -1)
xdotool windowactivate --sync $w; xdotool key Escape; sleep 1
xdotool mousemove 1065 85 sleep 1 click 1 sleep 2 mousemove 950 361 sleep 1 click 1
sleep 8
grep -E "CRITICAL|^#|signal SIG|Title|SetTitle|Parent|Natural|Window" /tmp/e2.out | cut -c1-230 | head -40
pkill -x gdb; pkill -9 -x epiphany
