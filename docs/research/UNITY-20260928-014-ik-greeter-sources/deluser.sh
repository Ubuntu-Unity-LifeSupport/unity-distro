#!/bin/bash
# deluser.sh - UNITY-20260928-014 (Design Challenger round 1, point 2), on target2
# at the unity-greeter login screen. A user deleted while accounts-daemon is
# down: does its object stay listed with no data, and what do the greeter's
# settings end up as? Creates ik014del (xkb de), lets the greeter pick it up,
# stops the daemon, deletes the user, starts the daemon; list-users-probe.py
# (as mike) and gsettings monitor (as lightdm) watch throughout.
set -u
TU=ik014del
LUID=$(id -u lightdm)
BUS=unix:path=/run/user/$LUID/bus
as_lightdm() { sudo -n -u lightdm env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID "$@"; }
stamp() { date -u +%T.%N | cut -c1-12; }
state() { echo "sources=$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"; }

echo "# $(date -u +%FT%TZ) indicator-keyboard=$(dpkg-query -W -f='${Version}' indicator-keyboard)"
id "$TU" >/dev/null 2>&1 || sudo -n useradd -m -s /bin/bash "$TU"
printf '[User]\nSystemAccount=false\n\n[InputSource0]\nxkb=de\n' | sudo -n tee /var/lib/AccountsService/users/$TU >/dev/null
sudo -n systemctl restart accounts-daemon
sleep 4
echo "$(stamp) with $TU: $(state)"

python3 ~/list-users-probe.py 26 > /tmp/probe014.txt 2>&1 &
probe=$!
as_lightdm gsettings monitor org.gnome.desktop.input-sources 2>&1 | while IFS= read -r line; do echo "$(stamp) $line"; done &
sleep 3
echo "$(stamp) ACTION stop accounts-daemon"; sudo -n systemctl stop accounts-daemon
sleep 2
echo "$(stamp) ACTION userdel $TU"; sudo -n userdel -r "$TU" 2>/dev/null; sudo -n rm -f /var/lib/AccountsService/users/$TU
sleep 2
echo "$(stamp) ACTION start accounts-daemon"; sudo -n systemctl start accounts-daemon
sleep 15
for p in $(ps -u lightdm -o pid=,comm= | awk '$2=="gsettings"{print $1}'); do sudo -n kill "$p"; done
wait "$probe"
echo "$(stamp) end: $(state)"
echo "--- list-users-probe (as mike, seconds since its start)"
cat /tmp/probe014.txt
