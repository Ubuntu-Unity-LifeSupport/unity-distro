#!/bin/bash
# coldwatch.sh TAG - run as oem from the first seconds of a boot into the OEM
# first-time setup session. Records, by uptime, when xfwm4 starts, when the
# wallpaper and Calamares windows become viewable and who has focus, then
# prints the final stacking and what is on screen at 700,200.
up() { cut -d' ' -f1 /proc/uptime; }
echo "== ${1:-cold} start at uptime $(up)s  basicwallpaper sha256 $(sha256sum /usr/bin/basicwallpaper | cut -c1-12)"
until wm=$(pgrep -x xfwm4 | head -1); [ -n "$wm" ]; do
  awk -v a=$(up) 'BEGIN{exit !(a>400)}' && { echo "no xfwm4 by uptime 400 s"; exit 1; }
  sleep 0.2
done
echo "$(up) xfwm4 pid $wm"
export DISPLAY=:0
for i in $(seq 1 100); do grep -qz '^XAUTHORITY=' /proc/$wm/environ 2>/dev/null && break; sleep 0.2; done
eval "$(tr '\0' '\n' < /proc/$wm/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=' | sed 's/^/export /')"
w=; c=; last=; t0=$(up)
while :; do
  [ -z "$w" ] && w=$(xdotool search --onlyvisible --class basicwallpaper 2>/dev/null | head -1) && [ -n "$w" ] && echo "$(up) wallpaper viewable $w"
  [ -z "$c" ] && c=$(xdotool search --onlyvisible --class calamares 2>/dev/null | head -1) && [ -n "$c" ] && echo "$(up) calamares viewable $c"
  f=$(xdotool getwindowfocus 2>/dev/null)
  [ "$f" != "$last" ] && { echo "$(up) focus -> $f ($(xdotool getwindowname $f 2>/dev/null))"; last=$f; }
  if [ -n "$w" ] && [ -n "$c" ]; then
    [ -z "$both" ] && both=$(up)
    awk -v a=$(up) -v b=$both 'BEGIN{exit !(a-b>15)}' && break
  fi
  awk -v a=$(up) -v b=$t0 'BEGIN{exit !(a-b>300)}' && { echo "timeout"; break; }
  sleep 0.2
done
for x in $(xprop -root _NET_CLIENT_LIST_STACKING | sed 's/.*# //; s/,//g'); do
  printf '  %-10s %-36s %s\n' $x "$(xprop -id $x WM_CLASS | sed 's/.*= //')" \
    "$(xprop -id $x _NET_WM_STATE | sed 's/.*= //; s/_NET_WM_STATE_//g') | $(xprop -id $x _NET_WM_WINDOW_TYPE | sed 's/.*= //; s/_NET_WM_WINDOW_TYPE_//g')"
done
gnome-screenshot -f /tmp/b-cold.png 2>/dev/null
python3 -c "
from PIL import Image
p=Image.open('/tmp/b-cold.png').convert('RGB').getpixel((700,200))
print('$(up) pixel 700,200: #%02X%02X%02X' % p, '-> WALLPAPER on top' if p[0]<120 and p[2]>p[1] else '-> Calamares on top')"
