#!/bin/sh
# LP #2158965: start Chrome in a window under the session's LD_PRELOAD, interact,
# take screenshots. chrome-deco.sh <tag> [nopreload|old]
# old: the +unity2 library copied to /tmp/nocsd-u2 instead of the installed one
. ~/envt.sh
TAG=$1; OUT=/tmp/chrome-deco-$TAG; rm -rf $OUT /tmp/chx-$TAG; mkdir -p $OUT
echo "libgtk-nocsd0 $(dpkg-query -W -f='${Version}' libgtk-nocsd0); session LD_PRELOAD: $(systemctl --user show-environment | grep ^LD_PRELOAD)"
PRE=; [ "$2" = nopreload ] && PRE="-E LD_PRELOAD="
[ "$2" = old ] && PRE="-E LD_PRELOAD=libunity-gtk4-menu.so.0:/tmp/nocsd-u2/libgtk-nocsd.so.0"
systemd-run --user -q --unit=chrome-$TAG $PRE google-chrome --user-data-dir=/tmp/chx-$TAG \
  --no-first-run --no-default-browser-check --password-store=basic \
  --window-size=900,600 --window-position=250,150 about:blank
sleep 15
W=$(xdotool search --sync --onlyvisible --class google-chrome | tail -1)
P=$(systemctl --user show -p MainPID --value chrome-$TAG)
echo "chrome pid $P, nocsd: $(grep -m1 -o "/[^ ]*nocsd[^ ]*" /proc/$P/maps)"
gnome-screenshot -f $OUT/1-start.png 2>/dev/null
xdotool windowactivate --sync $W key ctrl+t; sleep 2; xdotool key ctrl+Tab; sleep 1
xdotool mousemove 700 450 click 1; sleep 1
xdotool key super; sleep 2; xdotool key Escape; sleep 1   # focus leaves and comes back
xdotool windowactivate --sync $W; sleep 5
gnome-screenshot -f $OUT/2-after.png 2>/dev/null
systemctl --user stop chrome-$TAG
echo "screenshots in $OUT"
