#!/bin/bash
# greeter-restart.sh - UNITY-20260927-024, on target2 at the greeter.
# Runs indicator-keyboard-service as lightdm on the greeter's session bus (as
# research/indicator-keyboard-2166139/ik.sh), restarts accounts-daemon, and
# records every change of the greeter's org.gnome.desktop.input-sources
# sources/current with a timestamp, to see whether the layouts written during
# the restart window recover. Prints the service's accountsservice/keyboard
# messages and whether it survived.
LUID=$(id -u lightdm)
BUS=unix:path=/run/user/$LUID/bus
as_lightdm() { sudo -n -u lightdm env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID "$@"; }
state() { echo "$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"; }

sudo -n pkill -u lightdm -x indicator-keybo
sleep 1
sudo -n -u lightdm bash -c "cd /tmp; exec env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID DISPLAY=:0 G_MESSAGES_DEBUG=all /usr/libexec/indicator-keyboard/indicator-keyboard-service" > /tmp/ik-greeter.out 2>&1 &
sleep 6
pid=$(pgrep -u lightdm -x indicator-keybo)
echo "service pid $pid; before: $(state)"

last=""
end=$((SECONDS + 12))
restarted=0
while [ $SECONDS -lt $end ]; do
    if [ $restarted = 0 ] && [ $SECONDS -ge $((end - 10)) ]; then
        echo "$(date +%T.%N | cut -c1-12) RESTART accounts-daemon"
        sudo -n systemctl restart accounts-daemon &
        restarted=1
    fi
    now=$(state)
    if [ "$now" != "$last" ]; then
        echo "$(date +%T.%N | cut -c1-12) $now"
        last=$now
    fi
done
if [ -n "$pid" ] && [ -d /proc/$pid ]; then echo "service alive"; else echo "service DEAD"; fi
grep -E "CRITICAL|WARNING|Segmentation|assertion" /tmp/ik-greeter.out | head -5
