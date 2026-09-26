#!/bin/bash
# load.sh - start every scope/lens D-Bus service by activation; owner after 6 s, errors from the journal
export $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep DBUS_SESSION)
for s in $(grep -l "unity-scope\|unity-lens\|Unity.Scope\|Unity.Lens" /usr/share/dbus-1/services/*.service); do
  n=$(sed -n 's/^Name=//p' $s); e=$(sed -n 's/^Exec=//p' $s | awk '{print $1" "$2}')
  since=$(date +%s)
  r=$(timeout 25 gdbus call --session -d org.freedesktop.DBus -o /org/freedesktop/DBus -m org.freedesktop.DBus.StartServiceByName "$n" 0 2>&1 | tr -d '\n' | cut -c1-110)
  sleep 6
  o=$(gdbus call --session -d org.freedesktop.DBus -o /org/freedesktop/DBus -m org.freedesktop.DBus.NameHasOwner "$n" 2>&1 | tr -d '(),\n')
  err=$(journalctl --user --since "@$since" --no-pager -o cat 2>/dev/null | grep -E "Error|Traceback|No module|not found|ImportError|exited|status=" | grep -v "^$" | tail -2 | tr '\n' ' ' | cut -c1-220)
  echo "$n | start: $r | owner: $o | $err"
done
