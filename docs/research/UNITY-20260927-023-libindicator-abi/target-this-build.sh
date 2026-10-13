#!/bin/sh
# this_build target check on target2 for libindicator +unity3 (UNITY-20260927-023) and
# indicator-datetime +unity3 (UNITY-20260927-026): gated .debs from file repositories
# /var/tmp/localrepo-<tag>, on the session that already has our repository (Clean-2).
# Usage (on target2, as mike): sh target-this-build.sh install li023 idt026 > log; reboot; sh target-this-build.sh session > log
set -u
phase=${1:-install}
echo "== $phase host=$(hostname) boot=$(cat /proc/sys/kernel/random/boot_id) utc=$(date -u +%FT%TZ)"
echo "== clock: $(timedatectl show -p NTPSynchronized -p TimeUSec | tr '\n' ' ')"
if [ "$phase" = install ]; then
    shift
    echo "== snapshot marker: ~/.dirty $( [ -e ~/.dirty ] && echo PRESENT || echo absent )"
    for tag in "$@"; do
        printf '%s\n' "deb [trusted=yes] file:/var/tmp/localrepo-$tag ./" \
            | sudo tee /etc/apt/sources.list.d/local-$tag.list >/dev/null
    done
    sudo apt-get update -q 2>&1 | grep -E '^(E|W):' | head
    for p in libindicator3-7 indicator-datetime; do echo "== policy $p"; apt-cache policy $p | sed -n '1,3p'; done
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q full-upgrade >/tmp/this-build-full-upgrade.log 2>&1; echo "full-upgrade rc=$?"
    grep -E '^(E|W):' /tmp/this-build-full-upgrade.log | head -3
    echo "== installed versions and the file-repository .debs they came from"
    for tag in "$@"; do
        for f in /var/tmp/localrepo-$tag/*.deb; do
            p=$(dpkg-deb -f "$f" Package); v=$(dpkg-deb -f "$f" Version)
            [ "$(dpkg-query -W -f='${Version}' "$p" 2>/dev/null)" = "$v" ] && echo "$p $v $(sha256sum "$f" | cut -d' ' -f1)"
        done
    done
    exit 0
fi
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
echo "== libindicator3-7 $(dpkg-query -W -f='${Version}' libindicator3-7), indicator-datetime $(dpkg-query -W -f='${Version}' indicator-datetime)"
lib=/usr/lib/x86_64-linux-gnu/libindicator3.so.7
sha256sum "$(readlink -f $lib)" /usr/lib/x86_64-linux-gnu/indicator-datetime/indicator-datetime-service 2>/dev/null
echo "exports=$(nm -D --defined-only $lib | grep -c .) ayatana_exports=$(nm -D --defined-only $lib | grep -c ayatana)"
for n in unity-panel-ser indicator-datet ayatana-indicat; do
    for pid in $(pgrep -u "$(id -u)" "$n"); do
        echo "$n pid=$pid exe=$(readlink /proc/$pid/exe) libindicator3=$(grep -c 'libindicator3.so' /proc/$pid/maps) deleted_maps=$(grep -c '(deleted)' /proc/$pid/maps)"
    done
done
echo "== indicator-datetime on the bus"
gdbus introspect --session --dest com.canonical.indicator.datetime --object-path /com/canonical/indicator/datetime/desktop 2>&1 | grep -c -E 'org.gtk.(Menus|Actions)'
gdbus call --session --dest com.canonical.indicator.datetime --object-path /com/canonical/indicator/datetime \
    --method org.gtk.Actions.Describe _header 2>&1 | grep -o "'label': <'[^']*'>" | head -1
echo "== warnings since boot"
journalctl --user -b --no-pager 2>/dev/null | grep -i -E '(unity-panel-service|indicator-datetime).*(critical|segfault|undefined symbol)' | tail -5
echo "== done"
