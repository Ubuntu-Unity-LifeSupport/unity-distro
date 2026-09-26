#!/bin/bash
# One-line summary of known issue #1 for a session of USER on DISPLAY, counting
# only unity-settings-daemon logs (/tmp/usd-PID.log, test wrapper) created after
# the marker file MARK (touched just before the login). Real input on the PS/2
# mouse by name. Agent A.  Usage: cursor-loop2.sh TAG USER DISPLAY MARK
T=$1; U=$2; D=$3; M=$4; X="sudo DISPLAY=$D XAUTHORITY=/var/run/lightdm/root/$D xdotool"
line="$T user=$U disp=$D"
logs=$(find /tmp -maxdepth 1 -name 'usd-*.log' -user $U -newer $M | sort)
for f in $logs; do p=${f##*/usd-}; p=${p%.log}
  h=$(grep -c "Attempting to hide" $f); s=$(grep -c "Attempting to show" $f)
  ex=$(grep -cE "Name taken|SettingsDaemon finished" $f)
  lost=$(grep -c "Lost or failed to acquire name org.gnome.Mutter.IdleMonitor" $f)
  if [ -d /proc/$p ]; then al=A; grep -q "unity-settings-daemon.service" /proc/$p/cgroup && l=U || l=X; else al=-; l=?; fi
  line="$line | $p:$al$l hide=$h show=$s exit=$ex lost=$lost"; done
N=$(grep -l "ImExPS/2" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5)
x0=$($X getmouselocation | cut -d' ' -f1-2); sudo ~/evinject.py /dev/input/$N 8 4 2; sleep 1; x1=$($X getmouselocation | cut -d' ' -f1-2)
line="$line || $N [$x0]->[$x1]:"
for f in $logs; do p=${f##*/usd-}; p=${p%.log}; [ -d /proc/$p ] || continue
  last=$(grep -E "Attempting to (hide|show)" $f | tail -1 | grep -oE "hide|show"); line="$line $p=${last:-none}"; done
echo "$line" | tee -a ~/cur/summary2
