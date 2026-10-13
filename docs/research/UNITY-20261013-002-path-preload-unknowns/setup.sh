#!/bin/bash
# setup.sh - UNITY-20261013-002 on target2 (as mike over ssh), after a restore of Clean-2:
#   1. confirm the restore from inside; 2. the live archive (key + sources in ~/b1302), full-upgrade;
#   3. libunity-gtk4-menu0 (UNITY-20260927-037), gcc-multilib (the biarch lib32 C library, libc6-i386), tmux;
#   4. t32.c built 64-bit and -m32 (biarch)
set -u
B=~/b1302
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b1301 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs); foreign architectures: $(dpkg --print-foreign-architectures | xargs)"
touch ~/.dirty
echo "== 2 live archive"
sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
grep -hE "^(Date)" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
echo "  left to upgrade: $(sudo apt-get -s full-upgrade | grep -c '^Inst')"
echo "== 3 packages"
P="libunity-gtk4-menu0 gcc gcc-multilib tmux x11-utils"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst.log 2>&1; echo "  install rc=$?"
for p in $P libgtk-nocsd0 libc6 libc6-i386 snapd flatpak; do
  dpkg-query -W -f='${Package}\t${Version}\n' $p 2>/dev/null || echo "  $p not installed"; done | sed 's/^/  /'
ls -l /usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0 /usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0 | sed 's/^/  /'
echo "== 4 t32"
gcc -O1 -o $B/t64 $B/t32.c && echo "  t64: $(file -b $B/t64 | cut -d, -f1-2)"
gcc -m32 -O1 -o $B/t32-biarch $B/t32.c && echo "  t32-biarch: $(file -b $B/t32-biarch | cut -d, -f1-2), interpreter $(readelf -l $B/t32-biarch | sed -n 's/.*interpreter: \(.*\)]/\1/p')"
