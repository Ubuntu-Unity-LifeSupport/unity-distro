#!/bin/bash
# live.sh - inside the running OEM session: Alt+Tab twice, then restart the
# wallpaper so it maps after Calamares (as on a slow first boot).
export DISPLAY=:0
wm=$(pgrep -x xfwm4 | head -1)
eval "$(tr '\0' '\n' < /proc/$wm/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=' | sed 's/^/export /')"
top() { gnome-screenshot -f /tmp/b-l.png 2>/dev/null; python3 -c "
from PIL import Image
p=Image.open('/tmp/b-l.png').convert('RGB').getpixel((700,200))
print('#%02X%02X%02X' % p, 'wallpaper' if p[0]<120 and p[2]>p[1] else 'Calamares')"; }
echo "start:        $(top)"
xdotool key alt+Tab; sleep 2; echo "alt+tab:      $(top)"
xdotool key alt+Tab; sleep 2; echo "alt+tab x2:   $(top)"
pkill -x basicwallpaper; sleep 2
setsid /usr/bin/basicwallpaper /usr/share/backgrounds/ubuntu-unity/ubuntu-unity-default.png </dev/null >/dev/null 2>&1 &
sleep 5; echo "late map:     $(top)   focus=$(xdotool getwindowfocus getwindowname 2>/dev/null)"
