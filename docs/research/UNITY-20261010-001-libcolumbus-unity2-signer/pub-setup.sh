#!/bin/bash
# pub-setup.sh - target verification of the publication, on target2 (as mike over ssh) after a restore of Clean-2:
#   1. confirm the restore from inside
#   2. the live archive the usual way (our key + unity-distro.sources, copied to ~/b1010 beforehand), no file
#      repository, no drop-in; apt full-upgrade; apt-cache policy; the downloaded .debs' sha256 (to compare with
#      the gated manifest)
set -u
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b025 ~/b001 ~/b013 ~/b1010/repo 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
dpkg-query -W hud libcolumbus1v5 libcolumbus1-common 2>&1 | sed 's/^/  /'
echo "  NTP $(timedatectl show -p NTPSynchronized --value)"
touch ~/.dirty
echo "== 2 live archive"
sudo install -m644 ~/b1010/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 ~/b1010/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"; grep -E "192\.168\.56\.10|^(W|E):" /tmp/upd.log | sed 's/^/  /'
grep -hE "^(Date|Valid-Until)" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
apt-cache policy libcolumbus1v5 libcolumbus1-common | sed 's/^/  /'
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
echo "  left to upgrade: $(sudo apt-get -s full-upgrade | grep -c '^Inst')"
dpkg-query -W hud libcolumbus1v5 libcolumbus1-common unity 2>&1 | sed 's/^/  /'
dpkg -V libcolumbus1v5 libcolumbus1-common; echo "  dpkg -V rc=$?"
for f in /var/cache/apt/archives/libcolumbus*_*.deb; do echo "  $(basename "$f") sha256 $(sha256sum < "$f" | cut -c1-64)"; done
