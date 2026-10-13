#!/bin/bash
# setup.sh - UNITY-20261012-003 on target2 (as mike over ssh), after a restore of Clean-2 and before any test:
#   1. confirm the restore from inside
#   2. the live archive the usual way (key + unity-distro.sources in ~/b1203, copied beforehand), apt full-upgrade
#   3. libunity-gtk4-menu0 (not pulled in by the upgrade, UNITY-20260927-037), the test tools and GTK4 applications
#      from the archive
set -u
B=~/b1203
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b0309 ~/b1012 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
dpkg-query -W libgtk-nocsd0 libunity-gtk4-menu0 unity 2>&1 | sed 's/^/  /'
touch ~/.dirty
echo "== 2 live archive"
sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
grep -hE "^(Date)" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
echo "  left to upgrade: $(sudo apt-get -s full-upgrade | grep -c '^Inst')"
echo "== 3 libunity-gtk4-menu0, tools and applications"
P="libunity-gtk4-menu0 xdotool x11-utils python3-gi gir1.2-gtk-4.0 dbus-bin gnome-text-editor gnome-calculator
   nautilus loupe baobab gnome-clocks"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst.log 2>&1; echo "  install rc=$?"
for p in $P libgtk-nocsd0 unity unity-gtk3-module bamfdaemon indicator-appmenu; do
  dpkg-query -W -f='${Package}\t${Version}\n' $p 2>/dev/null || echo "$p MISSING"; done | sed 's/^/  /'
ls /usr/lib/environment.d/ | sed 's/^/  environment.d: /'
