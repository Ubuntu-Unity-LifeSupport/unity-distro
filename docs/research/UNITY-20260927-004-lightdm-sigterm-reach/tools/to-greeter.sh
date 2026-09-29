#!/bin/sh
# UNITY-20260927-004: restart lightdm (mike logs in automatically), log mike
# out once his session is settled, and wait for the greeter. Run as root.
systemctl restart lightdm
i=0; until loginctl list-sessions --no-legend | awk '$3=="mike" && $4=="seat0"' | grep -q . || [ $i -ge 120 ]; do sleep 1; i=$((i+1)); done
sleep 45
setpriv --reuid=mike --regid=mike --init-groups env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager \
  --method org.gnome.SessionManager.Logout 1 >/dev/null
i=0; until pgrep -x lightdm-gtk-gre >/dev/null || [ $i -ge 90 ]; do sleep 1; i=$((i+1)); done
sleep 8
pgrep -x lightdm-gtk-gre >/dev/null && echo "greeter up" || echo "NO GREETER"
