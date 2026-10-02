#!/bin/sh
# Target verification of the hud publication on target2 (Clean-2): our repository as a user adds it,
# the normal full-upgrade path, no file repository. Phase "install" upgrades; phase "session EXPECTED_VERSION"
# runs after a reboot into the Unity session (lo7.sh in ~/b029).
# Usage (on target2, as mike): sh target-published.sh install > log; reboot; sh target-published.sh session 14.10+...+unity2 > log
set -u
phase=${1:-install}
echo "== $phase ${2:-} host=$(hostname) boot=$(cat /proc/sys/kernel/random/boot_id) utc=$(date -u +%FT%TZ)"
echo "== clock: $(timedatectl show -p NTPSynchronized -p TimeUSec | tr '\n' ' ')"
if [ "$phase" = install ]; then
    echo "== snapshot marker: ~/.dirty $( [ -e ~/.dirty ] && echo PRESENT || echo absent )"
    touch ~/.dirty
    sudo install -D -m 644 /tmp/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
    printf '%s\n' 'Types: deb' 'URIs: http://192.168.56.10:8080/' 'Suites: resolute' \
        'Components: main' 'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/unity-distro.asc' \
        | sudo tee /etc/apt/sources.list.d/unity-distro.sources >/dev/null
    sudo apt-get update -q 2>&1 | grep -E '^(E|W):' | head
    echo "== policy hud"; apt-cache policy hud | head -8
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q full-upgrade >/tmp/published-full-upgrade.log 2>&1; echo "full-upgrade rc=$?"
    grep -E '^(E|W):' /tmp/published-full-upgrade.log | head -3
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q install xdotool >/dev/null 2>&1; echo "xdotool rc=$?"
    echo "== installed: $(dpkg-query -W -f='${Package} ${Version} ${db:Status-Abbrev}' hud)"
    echo "== the .deb apt fetched: $(sha256sum /var/cache/apt/archives/hud_*.deb 2>/dev/null)"
    echo "== dpkg -V hud: $(dpkg -V hud 2>&1 | wc -l) lines"
    exit 0
fi
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
echo "== hud installed: $(dpkg-query -W -f='${Version}' hud) (expected ${2:-?})"
for b in /usr/lib/x86_64-linux-gnu/hud/hud-service /usr/lib/x86_64-linux-gnu/hud/window-stack-bridge; do sha256sum "$b"; done
for n in hud-service window-stack-br; do
    pid=$(pgrep -u "$(id -u)" -x "$n" | head -1)
    echo "$n pid=$pid exe=$(readlink /proc/$pid/exe) deleted_maps=$(grep -c '(deleted)' /proc/$pid/maps)"
done
echo "== lo7.sh 10 (GAP=3 WATCH_DELAY=0)"
GAP=3 WATCH_DELAY=0 bash ~/b029/lo7.sh 10 2>&1 | grep '^run'
echo "== warnings since boot"
journalctl --user -b --no-pager 2>/dev/null | grep -E 'window-stack-bridge|hud-service' | grep -i -E 'critical|segfault|abort' | tail -5
echo "== done"
