#!/bin/bash
# probe.sh [TAG] - run as oem inside the OEM first-time setup session. Waits for
# the Calamares and basicwallpaper windows, then reports the stacking order,
# the focused window and what is on screen at 700,200 (Calamares' page area).
export DISPLAY=:0
wm=$(pgrep -x xfwm4 | head -1)
[ -n "$wm" ] || { echo "no xfwm4 - not the OEM session"; exit 1; }
eval "$(tr '\0' '\n' < /proc/$wm/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=' | sed 's/^/export /')"
for i in $(seq 1 120); do
  c=$(xdotool search --class calamares 2>/dev/null | head -1)
  w=$(xdotool search --class basicwallpaper 2>/dev/null | head -1)
  [ -n "$c" ] && [ -n "$w" ] && break; sleep 1
done
sleep 10
echo "== ${1:-probe} uptime $(cut -d' ' -f1 /proc/uptime)s  basicwallpaper sha256 $(sha256sum /usr/bin/basicwallpaper | cut -c1-12)"
echo "focus: $(xdotool getwindowfocus 2>/dev/null) ($(xdotool getwindowfocus getwindowname 2>/dev/null))"
for x in $(xprop -root _NET_CLIENT_LIST_STACKING | sed 's/.*# //; s/,//g'); do
  printf '  %-10s %-36s %s | %s\n' $x "$(xprop -id $x WM_CLASS | sed 's/.*= //')" \
    "$(xprop -id $x _NET_WM_STATE | sed 's/.*= //; s/_NET_WM_STATE_//g')" \
    "$(xprop -id $x _NET_WM_WINDOW_TYPE | sed 's/.*= //; s/_NET_WM_WINDOW_TYPE_//g')"
done
gnome-screenshot -f /tmp/b-probe.png 2>/dev/null
python3 -c "
from PIL import Image
p=Image.open('/tmp/b-probe.png').convert('RGB').getpixel((700,200))
print('pixel 700,200: #%02X%02X%02X' % p, '-> wallpaper on top' if p[0]<120 and p[2]>p[1] else '-> Calamares on top')"
