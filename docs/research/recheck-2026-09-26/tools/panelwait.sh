#!/bin/bash
# After boot: seconds from boot until compiz runs, and until Unity's panel is
# actually drawn (red channel of a panel pixel in a gnome-screenshot). Agent A.
. ~/envt.sh; b=$(date -d "$(uptime -s)" +%s)
while ! pgrep -u mike -x compiz >/dev/null; do sleep 1; done; c=$(( $(date +%s) - b ))
px() { python3 -c "
import gi; gi.require_version('GdkPixbuf','2.0'); from gi.repository import GdkPixbuf
p=GdkPixbuf.Pixbuf.new_from_file('/tmp/pw.png'); d=p.get_pixels(); print(d[14*p.get_rowstride()+640*p.get_n_channels()])" 2>/dev/null; }
for i in $(seq 1 120); do
  gnome-screenshot -f /tmp/pw.png 2>/dev/null; v=$(px)
  [ -n "$v" ] && [ "$v" -lt 50 ] && { echo "boot=$(uptime -s) compiz@+${c}s panel@+$(( $(date +%s) - b ))s"; exit; }
  sleep 2
done; echo "boot=$(uptime -s) compiz@+${c}s panel not drawn within 240 s"
