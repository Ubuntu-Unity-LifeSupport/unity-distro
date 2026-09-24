#!/bin/bash
# check.sh WP - with basicwallpaper binary WP on Xvfb :7: (1) session start in the
# script's order, (2) Alt+Tab, (3) wallpaper started 15 s after Calamares.
export DISPLAY=:7 WP=$1
top() { import -window root -crop 1x1+700+200 txt:- | tail -1 | grep -o '#[0-9A-F]*' | cut -c1-7; }
clean() { sudo -n pkill -x calamares; pkill -x basicwallpaper; pkill -x xfwm4; sleep 2; }
clean
setsid dbus-run-session ~/b/oemenv.sh :7 </dev/null >/dev/null 2>&1 &
sleep 20; echo "1 start:    $(top)"; ~/b/stack.sh :7 | sed 1d
import -window root /tmp/b-chk1.png
xdotool key alt+Tab; sleep 2; echo "2 alt+tab:  $(top)"
xdotool key alt+Tab; sleep 2; echo "2 alt+tab2: $(top)"
clean
(setsid dbus-run-session bash -c "xfwm4 & sleep 1; sudo -n calamares -D8 -c /tmp/oemcfg/etc/calamares" </dev/null >/dev/null 2>&1 &)
sleep 15; $WP /usr/share/backgrounds/ubuntu-unity/ubuntu-unity-default.png >/dev/null 2>&1 &
sleep 4; echo "3 late wp:  $(top)"; ~/b/stack.sh :7 | sed 1d
xdotool key super+d 2>/dev/null; true
clean
