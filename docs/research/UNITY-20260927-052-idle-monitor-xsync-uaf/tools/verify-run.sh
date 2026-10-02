#!/bin/bash
# UNITY-20260927-052 (agent A): the Design Challenger's test plan, identical
# for the unfixed and the fixed build. Real mouse input = the PS/2 mouse's
# existing evdev node, found by name (~/evinject.py). Scripts are copied to
# the target's home directory from this tools/ directory before the run.
#  B  a kept client's user-active and idle watches after two clients leave
#  C  well-behaved clients (RemoveWatch, then exit) x2
#  A  two clients leave without RemoveWatch (the crash reproducer)
. ~/envt.sh
N=$(grep -l "ImExPS/2" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5)
move() { sudo ~/evinject.py /dev/input/$N 8 4 2 >/dev/null; }
pid() { pgrep -x unity-settings-; }
echo "== u-s-d $(dpkg-query -W -f '${Version}' unity-settings-daemon), pid $(pid)"
echo "== B: kept client, two others leave, then input, then idle"
python3 ~/watch-listener.py 4000 30 > /tmp/listener.txt 2>&1 & L=$!
sleep 2
python3 ~/watch-client.py active; python3 ~/watch-client.py active; sleep 3
P1=$(pid); echo "  after the two departures ($(date +%T)): pid $P1"
move; echo "  input at $(date +%T)"; sleep 8   # user-active should fire now, then idle > 4 s
wait $L; sed 's/^/  listener: /' /tmp/listener.txt
echo "== C: RemoveWatch then exit, twice"
P0=$(pid); python3 ~/watch-client.py active --remove; python3 ~/watch-client.py active --remove; sleep 5
[ "$P0" = "$(pid)" ] && echo "  daemon survived (pid $P0)" || echo "  DAEMON DIED ($P0 -> $(pid))"
echo "== A: two clients leave without RemoveWatch"
~/two-clients.sh | sed 's/^/  /'
