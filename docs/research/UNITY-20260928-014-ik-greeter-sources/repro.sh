#!/bin/bash
# repro.sh - UNITY-20260928-014, on target2 at the unity-greeter login screen.
# Watches the lightdm user's org.gnome.desktop.input-sources (sources, current)
# with `gsettings monitor` (event-driven, every write is seen), then acts on
# accounts-daemon and reports what indicator-keyboard-service wrote and whether
# it survived. Usage: repro.sh restart|stop [watch-seconds]
#   restart: systemctl restart accounts-daemon (the reload window)
#   stop:    systemctl stop accounts-daemon, watch, then start it again
set -u
MODE=${1:-restart}
WATCH=${2:-12}
LUID=$(id -u lightdm)
BUS=unix:path=/run/user/$LUID/bus
as_lightdm() { sudo -n -u lightdm env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID "$@"; }
stamp() { date -u +%T.%N | cut -c1-12; }
svc_pid() { ps -u lightdm -o pid=,comm= | awk '$2=="indicator-keybo"{print $1}'; }

echo "# $(date -u +%FT%TZ) mode=$MODE host=$(hostname) indicator-keyboard=$(dpkg-query -W -f='${Version}' indicator-keyboard)"
pid0=$(svc_pid)
echo "service pid before: ${pid0:-none}"
[ -n "$pid0" ] && echo "service env: $(sudo -n cat /proc/$pid0/environ | tr "\0" " " | grep -o 'UNITY_GREETER_DBUS_NAME=[^ ]*\|DISPLAY=[^ ]*' | tr '\n' ' ')"
echo "$(stamp) before: sources=$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"

as_lightdm gsettings monitor org.gnome.desktop.input-sources 2>&1 | while IFS= read -r line; do
    echo "$(stamp) $line"
done &
mon=$!
sleep 2
since=$(date '+%F %T')
echo "$(stamp) ACTION $MODE accounts-daemon"
sudo -n systemctl "$MODE" accounts-daemon
sleep "$WATCH"
if [ "$MODE" = stop ]; then
    echo "$(stamp) after ${WATCH}s stopped: sources=$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"
    echo "$(stamp) ACTION start accounts-daemon"
    sudo -n systemctl start accounts-daemon
    sleep 6
fi
kill "$mon" 2>/dev/null
# the monitor's own gsettings process is a child of the sudo in the pipeline
for p in $(ps -u lightdm -o pid=,comm= | awk '$2=="gsettings"{print $1}'); do sudo -n kill "$p"; done
wait 2>/dev/null
pid1=$(svc_pid)
echo "$(stamp) end: sources=$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"
echo "service pid after: ${pid1:-none} ($([ "$pid0" = "$pid1" ] && echo same || echo CHANGED))"
sudo -n journalctl --since "$since" --no-pager -o short-precise 2>/dev/null | grep -iE "indicator-keyboard|segfault|core-dump|dumped core" | head -8
