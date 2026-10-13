#!/bin/sh
# Target verification of the libindicator / indicator-datetime publication on target2 (Clean-2): our
# repository as a user adds it, the normal full-upgrade path, no file repository. Phase "install"
# upgrades; phase "session" runs after a reboot into the Unity session (mmclient.py in ~/b029).
# Usage (on target2, as mike): sh target-published.sh install > log; reboot; sh target-published.sh session > log
set -u
phase=${1:-install}
echo "== $phase host=$(hostname) boot=$(cat /proc/sys/kernel/random/boot_id) utc=$(date -u +%FT%TZ)"
echo "== clock: $(timedatectl show -p NTPSynchronized -p TimeUSec | tr '\n' ' ')"
if [ "$phase" = install ]; then
    echo "== snapshot marker: ~/.dirty $( [ -e ~/.dirty ] && echo PRESENT || echo absent )"
    touch ~/.dirty
    sudo install -D -m 644 /tmp/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
    printf '%s\n' 'Types: deb' 'URIs: http://192.168.56.10:8080/' 'Suites: resolute' \
        'Components: main' 'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/unity-distro.asc' \
        | sudo tee /etc/apt/sources.list.d/unity-distro.sources >/dev/null
    sudo apt-get update -q 2>&1 | grep -E '^(E|W):' | head
    for p in libindicator3-7 indicator-datetime; do echo "== policy $p"; apt-cache policy $p | sed -n '1,3p'; done
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q full-upgrade >/tmp/published-full-upgrade.log 2>&1; echo "full-upgrade rc=$?"
    grep -E '^(E|W):' /tmp/published-full-upgrade.log | head -3
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q install gir1.2-messagingmenu-1.0 >/dev/null 2>&1; echo "gir1.2-messagingmenu-1.0 rc=$?"
    echo "== installed"
    dpkg-query -W -f='${Package} ${Version} ${db:Status-Abbrev}\n' libindicator3-7 indicator-common indicator-datetime
    echo "== the .debs apt fetched"
    sha256sum /var/cache/apt/archives/libindicator3-7_*.deb /var/cache/apt/archives/indicator-common_*.deb /var/cache/apt/archives/indicator-datetime_*.deb 2>/dev/null
    echo "== dpkg -V: $(dpkg -V libindicator3-7 indicator-common indicator-datetime 2>&1 | wc -l) lines"
    exit 0
fi
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
echo "== libindicator3-7 $(dpkg-query -W -f='${Version}' libindicator3-7), indicator-datetime $(dpkg-query -W -f='${Version}' indicator-datetime)"
lib=/usr/lib/x86_64-linux-gnu/libindicator3.so.7
sha256sum "$(readlink -f $lib)" /usr/lib/x86_64-linux-gnu/indicator-datetime/indicator-datetime-service
echo "exports=$(nm -D --defined-only $lib | grep -c .) ayatana_exports=$(nm -D --defined-only $lib | grep -c ayatana)"
for n in unity-panel-ser indicator-datet; do
    for pid in $(pgrep -u "$(id -u)" "$n"); do
        echo "$n pid=$pid exe=$(readlink /proc/$pid/exe) libindicator3=$(grep -c 'libindicator3.so' /proc/$pid/maps) deleted_maps=$(grep -c '(deleted)' /proc/$pid/maps) deleted_libs=$(grep '(deleted)' /proc/$pid/maps | grep -c '\.so')"
    done
done
echo "== panel entries (Sync)"
gdbus call --session --dest com.canonical.Unity.Panel.Service.Desktop --object-path /com/canonical/Unity/Panel/Service \
    --method com.canonical.Unity.Panel.Service.Sync 2>&1 | grep -o -E "(org\.ayatana\.indicator\.[a-z]+|com\.canonical\.indicator\.[a-z]+|libapplication\.so)" | sort -u | tr '\n' ' '; echo
echo "== datetime header"
gdbus call --session --dest com.canonical.indicator.datetime --object-path /com/canonical/indicator/datetime \
    --method org.gtk.Actions.DescribeAll 2>&1 | grep -o "desktop-header[^}]*}" | head -1 | cut -c1-200
echo "== messaging menu with a client"
nohup python3 ~/b029/mmclient.py pluma.desktop 40 > ~/b029/mmclient.log 2>&1 &
sleep 6; cat ~/b029/mmclient.log
gdbus call --session --dest com.canonical.Unity.Panel.Service.Desktop --object-path /com/canonical/Unity/Panel/Service \
    --method com.canonical.Unity.Panel.Service.Sync 2>&1 | grep -o "org.ayatana.indicator.messages[^)]*)" | head -1 | cut -c1-200
echo "== warnings since boot"
journalctl --user -b --no-pager 2>/dev/null | grep -i -E '(unity-panel-service|indicator-datetime).*(critical|segfault|undefined symbol)' | tail -5
echo "== done"
