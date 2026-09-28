#!/bin/sh
# UNITY-20260927-037 reproduction on target2 (Clean-2): add our repository as
# a user would, full-upgrade, and record whether libunity-gtk4-menu0 is
# installed and what pulls or would pull it.
# Usage (on target2, as mike): sh repro.sh <phase> > log; phase = before|after
# The key is expected at /tmp/unity-distro.asc (copied from builder).
set -u
phase=${1:-before}
echo "== $phase host=$(hostname) boot=$(cat /proc/sys/kernel/random/boot_id) utc=$(date -u +%FT%TZ)"
echo "== snapshot marker: ~/.dirty $( [ -e ~/.dirty ] && echo PRESENT || echo absent )"
touch ~/.dirty
if [ "$phase" = before ]; then
    sudo install -D -m 644 /tmp/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
    printf '%s\n' 'Types: deb' 'URIs: http://192.168.56.10:8080/' 'Suites: resolute' \
        'Components: main' 'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/unity-distro.asc' \
        | sudo tee /etc/apt/sources.list.d/unity-distro.sources >/dev/null
fi
echo "== sources"; cat /etc/apt/sources.list.d/unity-distro.sources
echo "== apt-get update"; sudo apt-get update -q 2>&1 | grep -E '^(E|W):|192.168.56.10' | head
for p in ubuntu-unity-desktop libunity-gtk4-menu0 libgtk-nocsd0 unity-gtk-module-common; do
    echo "== policy $p"; apt-cache policy "$p" | head -4
done
echo "== dpkg-query before upgrade"
dpkg-query -W -f='${Package} ${Version} ${db:Status-Abbrev}\n' libunity-gtk4-menu0 libgtk-nocsd0 ubuntu-unity-desktop 2>&1
echo "== simulate full-upgrade: packages to be newly installed"
sudo apt-get -s -o Debug::NoLocking=1 full-upgrade 2>/dev/null | grep -E '^Inst ' | grep -v '\[' | head -40
echo "== full-upgrade"
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q full-upgrade 2>&1 | grep -E 'NEW packages|newly installed|^  |upgraded,' | head -40
echo "== dpkg-query after upgrade"
dpkg-query -W -f='${Package} ${Version} ${db:Status-Abbrev}\n' libunity-gtk4-menu0 libgtk-nocsd0 ubuntu-unity-desktop 2>&1
echo "== who depends on or recommends libunity-gtk4-menu0 (reverse, installed and candidates)"
apt-cache rdepends --recurse=no libunity-gtk4-menu0 2>&1 | head
echo "== ubuntu-unity-desktop candidate Recommends containing gtk4-menu / gtk-nocsd"
apt-cache show ubuntu-unity-desktop 2>/dev/null | grep -E '^(Version|Recommends):' | sed 's/, /\n    /g' | grep -E 'Version|gtk4-menu|gtk-nocsd'
echo "== environment.d snippet present"; ls -l /usr/lib/environment.d/60-unity-gtk4-menu.conf 2>&1
echo "== done"
