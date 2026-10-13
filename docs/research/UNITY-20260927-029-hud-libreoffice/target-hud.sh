#!/bin/sh
# hud target check on target2 (Clean-2) for UNITY-20260927-029 (+unity2) and
# UNITY-20260927-028 (+unity3): our repository as a user adds it, plus the
# gated hud .debs from a file repository /var/tmp/localrepo-<tag> (no aptly).
# Phase "install <tag>" adds that file repository and full-upgrades; phase
# "session" runs after a reboot into the Unity session (lo7.sh in ~/b029).
# Usage (on target2, as mike): sh target-hud.sh install unity2|unity3 > log; sh target-hud.sh session > log
set -u
phase=${1:-install}
echo "== $phase ${2:-} host=$(hostname) boot=$(cat /proc/sys/kernel/random/boot_id) utc=$(date -u +%FT%TZ)"
echo "== clock: $(timedatectl show -p NTPSynchronized -p TimeUSec | tr '\n' ' ')"
if [ "$phase" = install ]; then
    tag=$2
    echo "== snapshot marker: ~/.dirty $( [ -e ~/.dirty ] && echo PRESENT || echo absent )"
    if [ ! -e /etc/apt/sources.list.d/unity-distro.sources ]; then
        sudo install -D -m 644 /tmp/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
        printf '%s\n' 'Types: deb' 'URIs: http://192.168.56.10:8080/' 'Suites: resolute' \
            'Components: main' 'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/unity-distro.asc' \
            | sudo tee /etc/apt/sources.list.d/unity-distro.sources >/dev/null
    fi
    printf '%s\n' "deb [trusted=yes] file:/var/tmp/localrepo-$tag ./" \
        | sudo tee /etc/apt/sources.list.d/local-hud-$tag.list >/dev/null
    sudo apt-get update -q 2>&1 | grep -E '^(E|W):' | head
    echo "== policy hud"; apt-cache policy hud | head -8
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q full-upgrade >/tmp/hud-$tag-full-upgrade.log 2>&1; echo "full-upgrade rc=$?"
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q install xdotool >/tmp/hud-$tag-xdotool.log 2>&1; echo "xdotool rc=$?"
    echo "== installed hud packages"
    dpkg-query -W -f='${Package} ${Version} ${db:Status-Abbrev}\n' 'hud*' 'libhud*' 'gir1.2-hud*' 2>/dev/null | grep -v '^$'
    echo "== installed .deb sha256 (apt cache of the file repository is the file itself)"
    for f in /var/tmp/localrepo-$tag/*.deb; do
        p=$(dpkg-deb -f "$f" Package); v=$(dpkg-deb -f "$f" Version)
        [ "$(dpkg-query -W -f='${Version}' "$p" 2>/dev/null)" = "$v" ] && sha256sum "$f"
    done
    exit 0
fi
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
echo "== hud installed: $(dpkg-query -W -f='${Version}' hud)"
for b in /usr/lib/x86_64-linux-gnu/hud/hud-service /usr/lib/x86_64-linux-gnu/hud/window-stack-bridge; do sha256sum "$b"; done
for n in hud-service window-stack-br; do
    pid=$(pgrep -u "$(id -u)" -x "$n" | head -1)
    echo "$n pid=$pid exe=$(readlink /proc/$pid/exe) deleted_maps=$(grep -c '(deleted)' /proc/$pid/maps)"
done
echo "== lo7.sh 20 (GAP=3 WATCH_DELAY=0), as logs/05"
GAP=3 WATCH_DELAY=0 bash ~/b029/lo7.sh 20 2>&1 | grep '^run'
echo "== window-stack-bridge / hud-service warnings since boot"
journalctl --user -b --no-pager 2>/dev/null | grep -E 'window-stack-bridge|hud-service' | grep -i -E 'critical|segfault|abort|Could not get desktop file' | tail -8
echo "== done"
