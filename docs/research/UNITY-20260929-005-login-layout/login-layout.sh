#!/bin/bash
# login-layout.sh - UNITY-20260929-005, on target2 at the lightdm-gtk-greeter
# login screen (the image's default greeter; autologin disabled for the test).
# The greeter's indicator-keyboard-service is started by hand with DISPLAY=:0
# (as UNITY-20260927-024 logs/05: lightdm-gtk-greeter does not load it by
# default). For each case it records the greeter X display's layout
# (setxkbmap -query) before and after the service's start, and the stored
# settings. update_login_layout() -> LightDM.set_layout() is what moves the X
# layout, so the X layout shows whether it ran.
#   fresh: the lightdm user's input-sources keys reset (never written)
#   cur1:  sources [gb, us] and current 1 stored explicitly; X layout gb
set -u
LUID=$(id -u lightdm)
BUS=unix:path=/run/user/$LUID/bus
XA=/var/run/lightdm/root/:0
as_lightdm() { sudo -n -u lightdm env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID "$@"; }
xq() { sudo -n env DISPLAY=:0 XAUTHORITY=$XA setxkbmap -query | awk '/layout|variant/{printf "%s ", $0}'; }
state() { echo "sources=$(as_lightdm gsettings get org.gnome.desktop.input-sources sources) current=$(as_lightdm gsettings get org.gnome.desktop.input-sources current)"; }
svc_pids() { ps -u lightdm -o pid=,comm= | awk '$2=="indicator-keybo"{print $1}'; }

echo "# $(date -u +%FT%TZ) indicator-keyboard=$(dpkg-query -W -f='${Version}' indicator-keyboard) greeter=$(ps -u lightdm -o comm= | grep -m1 greeter)"
for case in fresh cur1; do
    for p in $(svc_pids); do sudo -n kill "$p"; done; sleep 1
    as_lightdm dconf reset -f /org/gnome/desktop/input-sources/
    if [ "$case" = cur1 ]; then
        as_lightdm gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'gb'), ('xkb', 'us')]"
        as_lightdm gsettings set org.gnome.desktop.input-sources current 1
    fi
    sudo -n env DISPLAY=:0 XAUTHORITY=$XA setxkbmap gb
    echo "--- $case: before: X $(xq)| $(state) | explicit keys: $(as_lightdm dconf list /org/gnome/desktop/input-sources/ | tr '\n' ' ')"
    sudo -n -u lightdm bash -c "cd /tmp; exec env DBUS_SESSION_BUS_ADDRESS=$BUS XDG_RUNTIME_DIR=/run/user/$LUID DISPLAY=:0 /usr/libexec/indicator-keyboard/indicator-keyboard-service" > /tmp/ik005-$case.out 2>&1 &
    sleep 8
    echo "    after start: X $(xq)| $(state) | pid $(svc_pids)"
done
for p in $(svc_pids); do sudo -n kill "$p"; done
