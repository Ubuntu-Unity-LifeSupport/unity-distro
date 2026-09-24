#!/bin/bash
# coldrun.sh TAG - on builder: find oem-test by MAC, wait for its ssh, copy
# coldwatch.sh over as early as possible and run it; save the screenshot.
S=/tmp/claude-1000/-home-claude/ff7c415d-a453-4b36-bf96-3ae4a13b23fd/scratchpad
O="-o ConnectTimeout=2 -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
for i in $(seq 1 600); do
  for ip in $(seq 101 115); do ping -c1 -W1 192.168.56.$ip >/dev/null 2>&1 & done; wait
  ip=$(ip neigh | grep -i '08:00:27:fc:1d:99' | grep -v FAILED | awk '{print $1}' | head -1)
  [ -n "$ip" ] && u=$(ssh $O oem@$ip "cut -d. -f1 /proc/uptime" 2>/dev/null) && [ "$u" -lt 150 ] && break
  sleep 0.5
done
echo "ssh as oem up at $ip ($(date -u +%T))"
scp $O $S/coldwatch.sh oem@$ip:/tmp/coldwatch.sh && timeout 900 ssh $O oem@$ip "bash /tmp/coldwatch.sh $1"
scp $O oem@$ip:/tmp/b-cold.png $S/$1.png 2>/dev/null && convert $S/$1.png -resize 50% $S/$1-s.png
