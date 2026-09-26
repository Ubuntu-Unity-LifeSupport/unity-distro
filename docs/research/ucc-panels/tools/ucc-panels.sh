#!/bin/bash
# A-7: open every unity-control-center panel on its own, screenshot it, record
# whether the process survived and what it logged. Agent A.
. ~/envt.sh; E=$(pgrep -u mike -x nemo-desktop | head -1); while IFS= read -r -d "" kv; do case "$kv" in XDG_CURRENT_DESKTOP=*|XDG_SESSION_DESKTOP=*|DESKTOP_SESSION=*|XDG_DATA_DIRS=*|GTK_MODULES=*|UBUNTU_MENUPROXY=*|LANG=*|LANGUAGE=*) export "$kv";; esac; done < /proc/$E/environ; D=~/ucc; mkdir -p "${D:?}"; rm -f "${D:?}"/*
for p in ${@:-activity-log-manager appearance bluetooth color datetime display info keyboard mouse network power printers region screen sharing sound universal-access user-accounts wacom}; do
  pkill -x unity-control-c; sleep 1; T0=$(date +%T)
  (setsid nohup unity-control-center $p >$D/$p.out 2>&1 < /dev/null &); sleep 7
  alive=$(pgrep -xc unity-control-c)
  W=$(xdotool search --onlyvisible --class unity-control-center | tail -1); title=$(xdotool getwindowname $W 2>/dev/null)
  gnome-screenshot -w -f $D/$p.png 2>/dev/null || gnome-screenshot -f $D/$p.png 2>/dev/null
  crit=$(grep -ciE "critical" $D/$p.out); warn=$(grep -ciE "warning" $D/$p.out)
  j=$(journalctl --user --since $T0 --no-pager | grep -ciE "unity-control-c.*(critical|segfault|core)")
  echo "$p | alive=$alive | title=$title | out: critical=$crit warning=$warn | journal-crit=$j"
done
pkill -x unity-control-c; ls /var/crash | tr "\n" " "
