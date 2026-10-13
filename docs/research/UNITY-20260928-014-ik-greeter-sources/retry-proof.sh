#!/bin/bash
# retry-proof.sh - UNITY-20260928-014 (Verifier round 1): make the recovered
# value differ from the stored one, so the skip-and-retry path is visible.
# Sets the greeter's sources to [fr] as lightdm (the service does not migrate
# on its own write-watch), restarts accounts-daemon and records every write.
# Expected on +unity4: no [] and no 4294967295, one write back to [gb, us]
# about 0.25 s after the manager's is-loaded (from the user-changed retry).
set -u
LUID=$(id -u lightdm)
BUS=unix:path=/run/user/$LUID/bus
as_lightdm() { sudo -n -u lightdm env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID "$@"; }
stamp() { date -u +%T.%N | cut -c1-12; }
state() { echo "sources=$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"; }
monitor() { as_lightdm timeout "$1" gsettings monitor org.gnome.desktop.input-sources 2>&1 | while IFS= read -r l; do echo "$(stamp) WRITE $l"; done; }

echo "# $(date -u +%FT%TZ) indicator-keyboard=$(dpkg-query -W -f='${Version}' indicator-keyboard)"
for r in 1 2 3; do
    as_lightdm gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'fr')]"
    sleep 2
    echo "--- run $r seeded: $(state)"
    monitor 7 & sleep 1.5
    echo "$(stamp) ACTION restart accounts-daemon"; sudo -n systemctl restart accounts-daemon; wait
    echo "$(stamp) after: $(state)"
done
