#!/bin/bash
# pinta081.sh - Pinta 3.1.2 (built here with dotnet-sdk-10.0, DOTNET_ROLL_FORWARD=Major) under our series and
# b76f3fb, global menu on, 3 starts each; audit.py 12 s after the start (Pinta adds its menu buttons after
# presenting the window). The packaged library is put back at the end.
set -u
S=~/b081/nocsd-60ec176/libgtk-nocsd.so.0
U=~/b081/nocsd-b76f3fb/libgtk-nocsd.so.0
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
for v in "S-on:$S:GTK_NOCSD_GLOBAL_MENU=1" "U-on:$U:GTK_NOCSD_MENU=1" "U-g2:$U:GTK_NOCSD_MENU=1 GTK_NOCSD_MENU_GROUP=2"; do
  IFS=: read name lib extra <<<"$v"
  sudo -n cp "$lib" $T.new && sudo -n mv $T.new $T
  for i in 1 2 3; do
    pkill -x Pinta; sleep 1
    env -i "${envs[@]}" $extra DOTNET_ROLL_FORWARD=Major ~/b081/Pinta-3.1.2/build/bin/Pinta > /tmp/pinta.out 2>&1 & p=$!
    sleep 12
    echo "=================== pinta-$name-$i (pid $p)"
    python3 ~/b/audit.py $p 2>&1 | sed "s/^/  /"
    kill $p; sleep 2
  done
done
pkill -x Pinta
sudo -n cp ~/b081/libgtk-nocsd.so.0.pkg $T.new && sudo -n mv $T.new $T
echo "packaged library restored: $(sha256sum $T | cut -c1-16)"
