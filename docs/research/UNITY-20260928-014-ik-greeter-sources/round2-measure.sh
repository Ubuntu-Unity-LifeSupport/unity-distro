#!/bin/bash
# round2-measure.sh - UNITY-20260928-014, DC round 2 measurements on target2
# (unity-greeter login screen). M1: does a FRESH process list a user deleted
# while the daemon was down? M3: two real users (mike gb,us + ik014two de),
# daemon restart - is a partial union written? M2: restart only the greeter's
# indicator-keyboard-service (manager loaded at its start), then add a user
# (ik014new, xkb fr) + daemon restart - is fr missing (stale snapshot)?
set -u
LUID=$(id -u lightdm)
BUS=unix:path=/run/user/$LUID/bus
as_lightdm() { sudo -n -u lightdm env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID "$@"; }
stamp() { date -u +%T.%N | cut -c1-12; }
state() { echo "sources=$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"; }
monitor() { as_lightdm timeout "$1" gsettings monitor org.gnome.desktop.input-sources 2>&1 | while IFS= read -r l; do echo "$(stamp) $l"; done; }
mkuser() { id "$1" >/dev/null 2>&1 || sudo -n useradd -m -s /bin/bash "$1"; printf '[User]\nSystemAccount=false\n\n[InputSource0]\nxkb=%s\n' "$2" | sudo -n tee /var/lib/AccountsService/users/$1 >/dev/null; }
freshlist() { python3 -c '
import gi; gi.require_version("AccountsService","1.0")
from gi.repository import AccountsService, GLib
m=AccountsService.UserManager.get_default(); l=GLib.MainLoop()
def done(*a):
    if m.props.is_loaded:
        print("fresh process list_users:", [(u.get_object_path(), u.get_user_name(), u.is_loaded()) for u in m.list_users()]); l.quit()
m.connect("notify::is-loaded", done); GLib.timeout_add(3000, l.quit); done(); l.run()'; }

echo "# $(date -u +%FT%TZ) indicator-keyboard=$(dpkg-query -W -f='${Version}' indicator-keyboard)"
echo "## M1"; freshlist

echo "## M3 two real users"
mkuser ik014two de
sudo -n systemctl restart accounts-daemon; sleep 4
echo "$(stamp) with ik014two: $(state)"
monitor 10 & sleep 2; echo "$(stamp) ACTION restart accounts-daemon"; sudo -n systemctl restart accounts-daemon; wait
echo "$(stamp) end M3: $(state)"

echo "## M2 service-only restart, then new user + daemon restart"
as_lightdm systemctl --user restart indicator-keyboard.service; sleep 6
echo "$(stamp) after service restart: $(state)"
mkuser ik014new fr
monitor 10 & sleep 2; echo "$(stamp) ACTION restart accounts-daemon"; sudo -n systemctl restart accounts-daemon; wait
echo "$(stamp) end M2: $(state)"
for u in ik014two ik014new; do sudo -n userdel -r "$u" 2>/dev/null; sudo -n rm -f /var/lib/AccountsService/users/$u; done
sudo -n systemctl restart accounts-daemon; sleep 4
echo "$(stamp) test users removed: $(state)"
