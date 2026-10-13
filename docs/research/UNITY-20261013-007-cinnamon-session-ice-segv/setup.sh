#!/bin/bash
# setup.sh - UNITY-20261013-007 on target2 (as mike over ssh), after a restore of Clean-2:
#   1. confirm the restore from inside
#   2. the live archive (key + unity-distro.sources in ~/b1307, copied beforehand), apt full-upgrade
#   3. this build of cinnamon-session (6.4.2-1+unity6, ~/b1307/*.deb, copied beforehand) with dpkg -i;
#      bpftrace and xterm (an ordinary XSMP client) for the observation
set -u
B=~/b1307
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b1302 ~/b1204 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
dpkg-query -W cinnamon-session 2>&1 | sed 's/^/  /'
touch ~/.dirty
echo "== 2 live archive"
sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
grep -hE "^(Date)" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
for i in $(seq 120); do pgrep -x unattended-upgr > /dev/null || break; sleep 10; done
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
echo "  left to upgrade: $(sudo apt-get -s full-upgrade | grep -c '^Inst')"
echo "== 3 this build, bpftrace, xterm"
sha256sum $B/*.deb | cut -c1-16,65- | sed 's/^/  /'
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q bpftrace xterm libunity-gtk4-menu0 > /tmp/inst.log 2>&1; echo "  install rc=$?"
sudo dpkg -i $B/cinnamon-session_6.4.2-1+unity6_amd64.deb $B/cinnamon-session-common_6.4.2-1+unity6_all.deb > /tmp/dpkg.log 2>&1; echo "  dpkg -i rc=$?"
dpkg-query -W cinnamon-session cinnamon-session-common bpftrace xterm libice6 libsm6 compiz-core libgtk-nocsd0 unity | sed 's/^/  /'
dpkg -V cinnamon-session cinnamon-session-common; echo "  dpkg -V rc=$?"
