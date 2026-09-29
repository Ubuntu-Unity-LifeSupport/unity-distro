#!/bin/bash
# persist.sh - UNITY-20260928-014, on target2 at the unity-greeter login screen.
# Can the reload-window values outlive the window? Restarts accounts-daemon,
# and the moment the greeter's settings show sources=[] SIGKILLs
# indicator-keyboard-service (standing in for the greeter session ending
# inside the window). Then reads what is stored in the lightdm user's dconf and
# what the service writes after systemd's Restart=on-failure brings it back.
set -u
LUID=$(id -u lightdm)
BUS=unix:path=/run/user/$LUID/bus
as_lightdm() { sudo -n -u lightdm env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID "$@"; }
stamp() { date -u +%T.%N | cut -c1-12; }
svc_pid() { ps -u lightdm -o pid=,comm= | awk '$2=="indicator-keybo"{print $1}'; }
state() { echo "sources=$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"; }

echo "# $(date -u +%FT%TZ) indicator-keyboard=$(dpkg-query -W -f='${Version}' indicator-keyboard)"
pid0=$(svc_pid)
echo "$(stamp) service pid $pid0; before: $(state)"
( sleep 1; echo "$(stamp) ACTION restart accounts-daemon"; sudo -n systemctl restart accounts-daemon ) &
as_lightdm timeout 15 gsettings monitor org.gnome.desktop.input-sources 2>&1 | while IFS= read -r line; do
    echo "$(stamp) $line"
    case "$line" in
        "sources: @a(ss) []")
            sudo -n kill -KILL "$pid0" && echo "$(stamp) SIGKILL $pid0"
            break ;;
    esac
done
for p in $(ps -u lightdm -o pid=,comm= | awk '$2=="gsettings"{print $1}'); do sudo -n kill "$p"; done
echo "$(stamp) stored right after the kill: $(state)"
for i in $(seq 1 30); do
    p=$(svc_pid)
    [ -n "$p" ] && [ "$p" != "$pid0" ] && break
    sleep 0.5
done
echo "$(stamp) service back: pid ${p:-none}"
sleep 8
echo "$(stamp) after the new service settled: $(state)"
