#!/bin/bash
# oemenv.sh DISPLAY - run the OEM end-user session (start-ubuntu-unity-oem-env, verbatim
# order) on an existing X server, from the unpacked oemconfig in /tmp/oemcfg.
export DISPLAY=$1
export DESKTOP_SESSION='ubuntu-unity-oem-env'
/usr/bin/xfwm4 > /tmp/b-oem-xfwm4.log 2>&1 &
${WP:-/tmp/oemcfg/usr/bin/basicwallpaper} /usr/share/backgrounds/ubuntu-unity/ubuntu-unity-default.png > /tmp/b-oem-wp.log 2>&1 &
sudo -n /usr/bin/calamares -D8 -c /tmp/oemcfg/etc/calamares > /tmp/b-oem-cal.log 2>&1
