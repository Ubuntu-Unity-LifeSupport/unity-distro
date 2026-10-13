#!/bin/bash
# setup-tests.sh - UNITY-20261012-004 on target2 (as mike over ssh), after a restore of Clean-2: the live archive and
# full-upgrade, libunity-gtk4-menu0 from live (the control), and what the target tests need (test target only).
set -u
B=~/b1204t
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b1307 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
touch ~/.dirty
echo "== 2 live archive"
sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
grep -hE "^(Date)" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
for i in $(seq 120); do pgrep -x unattended-upgr > /dev/null || break; sleep 10; done
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
echo "== 3 the control library and the test tools"
P="libunity-gtk4-menu0 gcc pkg-config libgtk-4-dev libx11-dev xvfb xauth dbus-bin python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 xdotool x11-utils"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst.log 2>&1; echo "  install rc=$?"
for p in $P libgtk-4-1 libadwaita-1-0 libgtk-nocsd0 unity; do
  dpkg-query -W -f='${Package}\t${Version}\n' $p 2>/dev/null || echo "$p MISSING"; done | sed 's/^/  /'
