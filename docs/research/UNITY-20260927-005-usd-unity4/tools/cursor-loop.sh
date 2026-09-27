#!/bin/bash
# Summarise one login for known issue #1 in one line (agent A).
# For every unity-settings-daemon instance (test wrapper logs /tmp/usd-PID.log):
# alive?, hid/showed the cursor, exited, lost org.gnome.Mutter.IdleMonitor,
# launcher (U = systemd unit, X = xdg autostart). Then real input on the PS/2
# mouse, found BY NAME (event numbers change between boots), and the last
# cursor decision of each live instance.
T=$1; D=~/cur/$T; mkdir -p $D; . ~/envt.sh; cp /tmp/usd-*.log $D/ 2>/dev/null
node() { grep -l "$1" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5; }
line="$T boot=$(uptime -s)"
for f in $D/usd-*.log; do p=${f##*/usd-}; p=${p%.log}
  h=$(grep -c "Attempting to hide" $f); s=$(grep -c "Attempting to show" $f)
  ex=$(grep -cE "Name taken|SettingsDaemon finished" $f)
  lost=$(grep -c "Lost or failed to acquire name org.gnome.Mutter.IdleMonitor" $f)
  if [ -d /proc/$p ]; then al=A; grep -q "unity-settings-daemon.service" /proc/$p/cgroup && l=U || l=X; else al=-; l=?; fi
  line="$line | $p:$al$l hide=$h show=$s exit=$ex lost=$lost"; done
N=$(node "ImExPS/2"); x0=$(xdotool getmouselocation | cut -d' ' -f1-2)
sudo ~/evinject.py /dev/input/$N 8 4 2; sleep 1
x1=$(xdotool getmouselocation | cut -d' ' -f1-2)
line="$line || $N [$x0]->[$x1]:"
for f in /tmp/usd-*.log; do p=${f##*/usd-}; p=${p%.log}; [ -d /proc/$p ] || continue
  last=$(grep -E "Attempting to (hide|show)" $f | tail -1 | grep -oE "hide|show"); line="$line $p=${last:-none}"; done
echo "$line" | tee -a ~/cur/summary
