#!/bin/bash
# published-check.sh - on target2 (as mike over ssh), after a restore of Clean-2: the published unity-session
# 49.4+unity2 from the live archive alone. Confirm the restore, add the live archive, wait for unattended-upgrades and
# the dpkg lock, apt-get full-upgrade with apt's default, then what was fetched and installed.
set -u
B=~/b037
echo "== restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b037/repo 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
dpkg-query -W unity-session libunity-gtk4-menu0 2>&1 | sed 's/^/  /'
touch ~/.dirty
sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
sudo apt-get update -q > /tmp/upub.log 2>&1; echo "  update rc=$?"
grep -h '^Date' /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  live /'
apt-cache policy unity-session | sed -n 1,4p | sed 's/^/  /'
for i in $(seq 180); do
  n=$(ps -eo args | grep -c "[/]usr/bin/unattended-upgrade$"); l=$(sudo fuser /var/lib/dpkg/lock-frontend 2>/dev/null | wc -w)
  [ "$n" = 0 ] && [ "$l" = 0 ] && break; sleep 10
done
echo "== full-upgrade (install-recommends $(apt-config dump | grep -i 'APT::Install-Recommends ' | cut -d' ' -f2)) at $(date -u +%T)Z"
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fupub.log 2>&1; echo "  full-upgrade rc=$?"
grep -E '^(Get|Пол):.*(unity-session|libunity-gtk4-menu0) ' /tmp/fupub.log | sed 's/^/  /'
dpkg-query -W unity-session libunity-gtk4-menu0 libgtk-nocsd0 | sed 's/^/  /'
echo "  automatically installed: $(apt-mark showauto libunity-gtk4-menu0)"
sha256sum /var/cache/apt/archives/unity-session_49.4+unity2_all.deb /var/cache/apt/archives/libunity-gtk4-menu0_0.12_amd64.deb 2>&1 | sed 's/^/  /'
grep -hE " (install|upgrade) (unity-session|libunity-gtk4-menu0):" /var/log/dpkg.log /var/log/dpkg.log.1 2>/dev/null | tail -2 | sed 's/^/  /'
