#!/bin/bash
# target-setup.sh - on target2 (as mike, over ssh), after a restore of Clean-2:
#   1. confirm the restore from inside (no ~/.dirty, no work directories, only ubuntu.sources, archive versions)
#   2. the live archive the usual way (our key + unity-distro.sources, both copied to ~/b1010 beforehand) and
#      apt full-upgrade from it
#   3. libcolumbus +unity2 from a file repository of this task's build (~/b1010/repo, copied beforehand): every
#      binary of the source that is installed after step 2 is upgraded to +unity2; nothing else changes
set -u
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b025 ~/b001 ~/b013 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
dpkg-query -W hud libcolumbus1v5 libcolumbus1-common python3-columbus 2>&1 | sed 's/^/  /'
echo "  NTP $(timedatectl show -p NTPSynchronized --value)"
touch ~/.dirty
echo "== 2 live archive"
sudo install -m644 ~/b1010/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 ~/b1010/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"; grep -E "192\.168\.56\.10|^(W|E):" /tmp/upd.log | sed 's/^/  /'
grep -hE "^(Date|Valid-Until)" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
echo "  left to upgrade: $(sudo apt-get -s full-upgrade | grep -c '^Inst')"
dpkg-query -W hud libcolumbus1v5 libcolumbus1-common python3-columbus unity 2>&1 | sed 's/^/  /'
echo "== 3 +unity2 from the file repository"
# ~/b1010/repo/Packages is generated on the builder (apt-ftparchive packages . over the copied .debs) and copied
# here: apt-utils is not installed on target2. The first run of this script tried it here, got an empty index, and
# the install refused (rc 100); the index was then made on the builder and steps 3's update and install rerun.
echo "deb [trusted=yes] file:/home/mike/b1010/repo ./" | sudo tee /etc/apt/sources.list.d/b1010-local.list > /dev/null
sudo apt-get update -q > /tmp/upd2.log 2>&1; echo "  update rc=$?"
P=""
for d in ~/b1010/repo/*.deb; do n=$(dpkg-deb -f "$d" Package)
  dpkg-query -W -f='${Status}' "$n" 2>/dev/null | grep -q "ok installed" && P="$P $n=1.1.0+15.10.20150806-0ubuntu39+unity2"; done
echo "  installing:$P"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst.log 2>&1; echo "  install rc=$?"
grep -E "^(Обновление|Upgrading|Распаковывается|Unpacking)" /tmp/inst.log | sed 's/^/  /'
dpkg-query -W libcolumbus1v5 libcolumbus1-common python3-columbus 2>&1 | sed 's/^/  /'
dpkg -V libcolumbus1v5 libcolumbus1-common; echo "  dpkg -V rc=$?"
for d in ~/b1010/repo/*.deb; do n=$(dpkg-deb -f "$d" Package)
  dpkg-query -W -f='${Status}' "$n" 2>/dev/null | grep -q "ok installed" && echo "  $(basename "$d") sha256 $(sha256sum < "$d" | cut -c1-64)"; done
