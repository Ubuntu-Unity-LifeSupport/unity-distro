#!/bin/bash
# setup.sh - UNITY-20261009-003/-004/-005 on target2 (as mike over ssh), after a restore of Clean-2:
#   1. confirm the restore from inside
#   2. the live archive the usual way (key + unity-distro.sources in ~/b0309, copied beforehand), apt full-upgrade
#   3. test tools: xdotool, x11-utils, gdb, and for the -005 probe g++ and qtbase5-dev
set -u
B=~/b0309
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b1012 ~/b1010 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
dpkg-query -W hud gnome-terminal 2>&1 | sed 's/^/  /'
touch ~/.dirty
echo "== 2 live archive"
sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
grep -hE "^Date" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
echo "  left to upgrade: $(sudo apt-get -s full-upgrade | grep -c '^Inst')"
dpkg-query -W hud unity gnome-terminal libgtk-nocsd0 2>&1 | sed 's/^/  /'
echo "== 3 test tools"
P="xdotool x11-utils gdb g++ qtbase5-dev"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst.log 2>&1; echo "  install rc=$?"
grep -E "^E:" /tmp/inst.log | sed 's/^/  /'
for p in $P; do dpkg-query -W -f='${Package} ${Version}\n' $p 2>/dev/null || echo "$p MISSING"; done | sed 's/^/  /'
