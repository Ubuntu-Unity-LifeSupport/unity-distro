#!/bin/bash
# setup.sh - UNITY-20261012-004 on target2 (as mike over ssh), after a restore of Clean-2:
#   1. confirm the restore from inside
#   2. the live archive (key + unity-distro.sources in ~/b1204, copied beforehand), apt full-upgrade
#   3. libunity-gtk4-menu0 (not pulled in by the upgrade, UNITY-20260927-037), tools, dotnet-sdk-10.0
#   4. Pinta 3.1.2 from its release tag, built with dotnet (Gir.Core; runs with DOTNET_ROLL_FORWARD=Major), as in
#      UNITY-20261012-001 setup.sh step 5
set -u
B=~/b1204
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b1203 ~/b1012 2>&1 | sed 's/^/  /'
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
echo "== 3 libunity-gtk4-menu0, tools, dotnet"
P="libunity-gtk4-menu0 xdotool x11-utils python3-gi gir1.2-gtk-4.0 dbus-bin git dotnet-sdk-10.0"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst.log 2>&1; echo "  install rc=$?"
for p in $P libgtk-nocsd0 unity indicator-appmenu bamfdaemon libgtk-4-1; do
  dpkg-query -W -f='${Package}\t${Version}\n' $p 2>/dev/null || echo "$p MISSING"; done | sed 's/^/  /'
ls /usr/lib/environment.d/ | sed 's/^/  environment.d: /'
cat /usr/lib/environment.d/60-unity-gtk4-menu.conf | sed 's/^/  60-unity-gtk4-menu.conf: /'
echo "== 4 Pinta 3.1.2"
cd $B && git clone -q --depth 1 --branch 3.1.2 https://github.com/PintaProject/Pinta.git Pinta-3.1.2 2>&1 | grep -v detached | tail -2
cd $B/Pinta-3.1.2 && git log --oneline -1 | sed 's/^/  /'
dotnet build -c Release Pinta/Pinta.csproj -o $B/Pinta-3.1.2/build/bin > $B/pinta-build.log 2>&1; echo "  pinta build rc=$?"
tail -3 $B/pinta-build.log | sed 's/^/  /'
ls -la $B/Pinta-3.1.2/build/bin/Pinta 2>&1 | sed 's/^/  /'
