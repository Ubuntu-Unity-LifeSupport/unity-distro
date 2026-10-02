#!/bin/sh
# UNITY-20260927-023 target check on target2 (Clean-2): our repository as a
# user adds it, plus libindicator +unity3 from a file repository in
# /var/tmp/localrepo (no aptly). Phase "install" upgrades; phase "session"
# runs after a reboot into the Unity session.
# Usage (on target2, as mike): sh target.sh install|session > log
set -u
phase=${1:-install}
echo "== $phase host=$(hostname) boot=$(cat /proc/sys/kernel/random/boot_id) utc=$(date -u +%FT%TZ)"
if [ "$phase" = install ]; then
    echo "== snapshot marker: ~/.dirty $( [ -e ~/.dirty ] && echo PRESENT || echo absent )"
    touch ~/.dirty
    sudo install -D -m 644 /tmp/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
    printf '%s\n' 'Types: deb' 'URIs: http://192.168.56.10:8080/' 'Suites: resolute' \
        'Components: main' 'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/unity-distro.asc' \
        | sudo tee /etc/apt/sources.list.d/unity-distro.sources >/dev/null
    printf '%s\n' 'deb [trusted=yes] file:/var/tmp/localrepo ./' \
        | sudo tee /etc/apt/sources.list.d/local-023.list >/dev/null
    sudo apt-get update -q 2>&1 | grep -E '^(E|W):' | head
    echo "== policy libindicator3-7"; apt-cache policy libindicator3-7 | head -8
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q full-upgrade >/tmp/023-full-upgrade.log 2>&1; echo "full-upgrade rc=$?"
    dpkg-query -W -f='${Package} ${Version} ${db:Status-Abbrev}\n' libindicator3-7 ayatana-indicator-messages unity
    exit 0
fi
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
echo "== libindicator3-7 installed: $(dpkg-query -W -f='${Version}' libindicator3-7)"
echo "== exported symbols of the installed library"
nm -D --defined-only /usr/lib/x86_64-linux-gnu/libindicator3.so.7 | awk '{print $3}' | grep -c .
nm -D --defined-only /usr/lib/x86_64-linux-gnu/libindicator3.so.7 | grep -c ayatana
echo "== unity-panel-service maps libindicator3 and the messages indicator"
pid=$(pgrep -u "$(id -u)" -x unity-panel-ser | head -1)
echo "pid=$pid"; grep -o -E 'libindicator3\.so\.7[^ ]*' /proc/$pid/maps | sort -u
echo "== ayatana-indicator-messages service"
systemctl --user --no-pager status ayatana-indicator-messages.service 2>&1 | sed -n '1,4p'
echo "== panel entries (unity-panel-service Sync): indicator names"
gdbus call --session --dest com.canonical.Unity.Panel.Service --object-path /com/canonical/Unity/Panel/Service \
    --method com.canonical.Unity.Panel.Service.Sync 2>&1 | grep -o -E "'(libayatana|libapplication|ayatana|messag|com\.canonical|org\.ayatana)[^']*'" | sort -u | head -20
echo "== warnings from unity-panel-service since boot"
journalctl --user -b --no-pager 2>/dev/null | grep -i -E 'unity-panel-service.*(critical|warning|undefined symbol)|indicator_ng_ayatana' | tail -5
echo "== done"
