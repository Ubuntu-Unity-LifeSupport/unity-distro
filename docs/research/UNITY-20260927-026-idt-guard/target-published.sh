#!/bin/sh
# Target verification of the indicator-datetime publication on target2 (Clean-2): our repository as a
# user adds it, the normal full-upgrade path, no file repository. Phase "install" upgrades; phase
# "session" runs after a reboot into the Unity session.
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
    echo "== policy indicator-datetime"; apt-cache policy indicator-datetime | sed -n '1,3p'
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q full-upgrade >/tmp/published-full-upgrade.log 2>&1; echo "full-upgrade rc=$?"
    grep -E '^(E|W):' /tmp/published-full-upgrade.log | head -3
    echo "== installed: $(dpkg-query -W -f='${Package} ${Version} ${db:Status-Abbrev}' indicator-datetime)"
    echo "== the .deb apt fetched: $(sha256sum /var/cache/apt/archives/indicator-datetime_*.deb 2>/dev/null)"
    echo "== dpkg -V indicator-datetime: $(dpkg -V indicator-datetime 2>&1 | wc -l) lines"
    exit 0
fi
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
echo "== indicator-datetime installed: $(dpkg-query -W -f='${Version}' indicator-datetime)"
sha256sum /usr/lib/x86_64-linux-gnu/indicator-datetime/indicator-datetime-service
for pid in $(pgrep -u "$(id -u)" indicator-datet); do
    echo "indicator-datetime-service pid=$pid exe=$(readlink /proc/$pid/exe) deleted_maps=$(grep -c '(deleted)' /proc/$pid/maps) deleted_libs=$(grep '(deleted)' /proc/$pid/maps | grep -c '\.so')"
done
echo "== on the bus: $(gdbus introspect --session --dest com.canonical.indicator.datetime --object-path /com/canonical/indicator/datetime 2>&1 | grep -c 'interface org.gtk.Actions')"
echo "== datetime header"
gdbus call --session --dest com.canonical.indicator.datetime --object-path /com/canonical/indicator/datetime \
    --method org.gtk.Actions.DescribeAll 2>&1 | grep -o "desktop-header[^}]*}" | head -1 | cut -c1-200
echo "== panel lists datetime: $(gdbus call --session --dest com.canonical.Unity.Panel.Service.Desktop --object-path /com/canonical/Unity/Panel/Service --method com.canonical.Unity.Panel.Service.Sync 2>&1 | grep -c 'com.canonical.indicator.datetime')"
echo "== warnings since boot"
journalctl --user -b --no-pager 2>/dev/null | grep -i -E 'indicator-datetime.*(critical|segfault|abort)' | tail -5
echo "== done"
