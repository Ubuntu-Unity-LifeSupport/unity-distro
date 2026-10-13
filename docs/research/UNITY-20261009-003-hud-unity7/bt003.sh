#!/bin/bash
# bt003.sh - UNITY-20261009-003 path 1 under gdb: attach to the running hud-service (sudo: ptrace_scope 1), let it run,
# send a legacy StartQuery + ExecuteQuery with a D-Bus structure as the item key, print the backtrace at the crash.
set -u
B=~/b0309
export DISPLAY=:0
sp=$(pgrep -x compiz)
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud \
  --method org.freedesktop.DBus.Properties.Get com.canonical.hud OpenQueries > /dev/null 2>&1; sleep 2
p=$(pgrep -x hud-service | head -1)
echo "hud-service $p ($(dpkg-query -W -f='${Version}' hud))"
sudo -n gdb -q -batch -p $p -ex "set pagination off" -ex continue -ex "bt 12" > $B/bt003.txt 2>&1 &
g=$!
sleep 4
python3 $B/hudexec.py "Создать окно" --key-struct
wait $g
grep -E "^#|SIGSEGV|Thread .* received" $B/bt003.txt | head -16
