#!/bin/bash
# validate.sh - UNITY-20260928-014 live validation of +unity4 on target2 at
# the unity-greeter login screen (normal boot). Pass criterion (card): no write
# of [] or of an index out of range, no write with different content between the
# good values and the recovered ones, recovery to the full union.
set -u
LUID=$(id -u lightdm)
BUS=unix:path=/run/user/$LUID/bus
as_lightdm() { sudo -n -u lightdm env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID "$@"; }
stamp() { date -u +%T.%N | cut -c1-12; }
svc_pid() { ps -u lightdm -o pid=,comm= | awk '$2=="indicator-keybo"{print $1}'; }
state() { echo "sources=$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"; }
monitor() { as_lightdm timeout "$1" gsettings monitor org.gnome.desktop.input-sources 2>&1 | while IFS= read -r l; do echo "$(stamp) WRITE $l"; done; }
mkuser() { id "$1" >/dev/null 2>&1 || sudo -n useradd -m -s /bin/bash "$1"; printf '[User]\nSystemAccount=false\n\n[InputSource0]\nxkb=%s\n' "$2" | sudo -n tee /var/lib/AccountsService/users/$1 >/dev/null; }
rmuser() { sudo -n userdel -r "$1" 2>/dev/null; sudo -n rm -f /var/lib/AccountsService/users/$1; }
restart_watch() {  # label, watch seconds
    echo "--- $1: pid $(svc_pid); before: $(state)"
    monitor "$2" & sleep 1.5
    echo "$(stamp) ACTION restart accounts-daemon"; sudo -n systemctl restart accounts-daemon; wait
    echo "$(stamp) after: $(state); pid $(svc_pid)"
}

echo "# $(date -u +%FT%TZ) indicator-keyboard=$(dpkg-query -W -f='${Version}' indicator-keyboard) pid $(svc_pid)"
echo "## V1 daemon restart x3 (mike: gb, us)"
for r in 1 2 3; do restart_watch "V1.$r" 6; done

echo "## V2 daemon stopped 15 s, then started"
monitor 24 & sleep 1.5
echo "$(stamp) ACTION stop"; sudo -n systemctl stop accounts-daemon; sleep 15
echo "$(stamp) stopped: $(state)"; echo "$(stamp) ACTION start"; sudo -n systemctl start accounts-daemon; wait
echo "$(stamp) after: $(state)"

echo "## V3 service killed 0.3 s after a daemon restart (inside the window), then a new user + daemon restart"
p0=$(svc_pid); monitor 12 & sleep 1.5
echo "$(stamp) ACTION restart accounts-daemon"; sudo -n systemctl restart accounts-daemon & sleep 0.3
sudo -n kill -KILL "$p0" && echo "$(stamp) SIGKILL $p0"; wait
echo "$(stamp) after the kill: $(state); pid $(svc_pid)"
mkuser ik014two de
restart_watch "V3 new user de in the restarted instance" 8

echo "## V4 multi-user daemon restarts x3 (mike gb,us + ik014two de + ik014new fr)"
mkuser ik014new fr
restart_watch "V4.0 pick up fr" 8
for r in 1 2 3; do restart_watch "V4.$r" 6; done

echo "## V5 service-only restart (M2), then remove the test users + daemon restart"
as_lightdm systemctl --user restart indicator-keyboard.service; sleep 6
echo "after service restart: $(state); pid $(svc_pid)"
rmuser ik014two; rmuser ik014new
restart_watch "V5 users removed" 8
sudo -n journalctl --since "-10min" --no-pager | grep -iE "indicator-keyboard-service|segfault" | grep -v GDK_IS_SCREEN | tail -5
