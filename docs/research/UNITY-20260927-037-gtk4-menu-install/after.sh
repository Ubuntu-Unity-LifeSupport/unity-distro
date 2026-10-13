#!/bin/sh
# UNITY-20260927-037 check of the fix on target2 (Clean-2): our repository as
# a user adds it, plus the locally built unity-session 49.4+unity2 from a
# file repository in /var/tmp/localrepo (no aptly involved).
# Usage (on target2, as mike): sh after.sh > log
set -u
echo "== after host=$(hostname) boot=$(cat /proc/sys/kernel/random/boot_id) utc=$(date -u +%FT%TZ)"
echo "== snapshot marker: ~/.dirty $( [ -e ~/.dirty ] && echo PRESENT || echo absent )"
touch ~/.dirty
sudo install -D -m 644 /tmp/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
printf '%s\n' 'Types: deb' 'URIs: http://192.168.56.10:8080/' 'Suites: resolute' \
    'Components: main' 'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/unity-distro.asc' \
    | sudo tee /etc/apt/sources.list.d/unity-distro.sources >/dev/null
printf '%s\n' 'deb [trusted=yes] file:/var/tmp/localrepo ./' \
    | sudo tee /etc/apt/sources.list.d/local-037.list >/dev/null
sudo apt-get update -q 2>&1 | grep -E '^(E|W):' | head
echo "== policy unity-session"; apt-cache policy unity-session | head -8
echo "== candidate Recommends"; apt-cache show unity-session=49.4+unity2 | grep -E '^(Version|Recommends):'
echo "== simulate apt-get upgrade (never installs new packages)"
sudo apt-get -s upgrade 2>/dev/null | grep -E '^Inst (unity-session|libunity-gtk4-menu0) |^  libunity-gtk4-menu0|kept back' | head
echo "== simulate full-upgrade"
sudo apt-get -s full-upgrade 2>/dev/null | grep -E '^Inst (unity-session|libunity-gtk4-menu0) ' | head
echo "== full-upgrade"
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q full-upgrade >/tmp/037-full-upgrade.log 2>&1; echo "rc=$?"
grep -E 'libunity-gtk4-menu0|unity-session' /tmp/037-full-upgrade.log | head
echo "== dpkg-query after"
dpkg-query -W -f='${Package} ${Version} ${db:Status-Abbrev}\n' unity-session libunity-gtk4-menu0 libgtk-nocsd0
echo "== apt-mark: libunity-gtk4-menu0 is $(apt-mark showauto libunity-gtk4-menu0 | grep -q . && echo auto || echo manual)"
echo "== reverse dependencies now"; apt-cache rdepends --installed libunity-gtk4-menu0 | sed -n '3,6p'
echo "== environment.d"; cat /usr/lib/environment.d/60-unity-gtk4-menu.conf
echo "== done"
