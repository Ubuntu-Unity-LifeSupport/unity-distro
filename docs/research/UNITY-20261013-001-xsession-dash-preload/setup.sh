#!/bin/bash
# setup.sh - UNITY-20261013-001 on target2 (as mike over ssh), after a restore of Clean-2:
#   1. confirm the restore from inside
#   2. the live archive (key + unity-distro.sources in ~/b1301, copied beforehand), apt full-upgrade
#   3. libunity-gtk4-menu0 (not pulled in by the upgrade, UNITY-20260927-037), a GTK3 and a GTK4 application,
#      tools; print the installed versions and the files that decide the X session start
set -u
B=~/b1301
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b1204 ~/.config/environment.d 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
echo "  lightdm.conf.d: $(ls /etc/lightdm/lightdm.conf.d/ 2>&1 | xargs)"
dpkg-query -W libgtk-nocsd0 libunity-gtk4-menu0 2>&1 | sed 's/^/  /'
touch ~/.dirty
echo "== 2 live archive"
sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
grep -hE "^(Date)" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
echo "  left to upgrade: $(sudo apt-get -s full-upgrade | grep -c '^Inst')"
echo "== 3 libunity-gtk4-menu0, applications, tools"
P="libunity-gtk4-menu0 gnome-disk-utility gnome-calculator xdotool x11-utils"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst.log 2>&1; echo "  install rc=$?"
for p in $P libgtk-nocsd0 lightdm unity x11-common dash; do
  dpkg-query -W -f='${Package}\t${Version}\n' $p 2>/dev/null || echo "$p MISSING"; done | sed 's/^/  /'
apt-cache policy libunity-gtk4-menu0 libgtk-nocsd0 | grep -E '^[a-z]|Installed|Установлен|Candidate|Кандидат' | sed 's/^/  /'
echo "  /bin/sh -> $(readlink -f /bin/sh); /etc/X11/Xsession: $(head -1 /etc/X11/Xsession)"
ls -l /usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0* /usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0* | sed 's/^/  /'
for f in /usr/lib/environment.d/50-gtk-nocsd.conf /usr/lib/environment.d/60-unity-gtk4-menu.conf; do
  sed "s|^|  $f: |" "$f"; done
echo "  /etc/X11/Xsession.d: $(ls /etc/X11/Xsession.d | xargs)"
echo "  /etc/X11/Xsession.d/51gtk-nocsd sha256 $(sha256sum < /etc/X11/Xsession.d/51gtk-nocsd | cut -c1-16)"
sudo lightdm --show-config 2>&1 | grep -iE 'session-wrapper|autologin|user-session' | sed 's/^/  lightdm: /'
