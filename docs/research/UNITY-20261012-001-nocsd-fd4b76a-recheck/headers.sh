#!/bin/bash
# headers.sh - 52fa72e / 5f5acae in real applications: each application started with b76f3fb and with fd4b76a
# (start.sh, menu switch on, our libunity-gtk4-menu not loaded), the focused window captured with its decoration
# (gnome-screenshot -w), the top 120 px kept; all strips put into one image (~/b1012/headers.png), b76f3fb left,
# fd4b76a right, one row per application. The window title and the header labels are listed too (xdotool, AT-SPI
# not used).
set -u
B=~/b1012
export DISPLAY=:0
APPS="nautilus gnome-text-editor gnome-calculator gnome-clocks loupe baobab"
mkdir -p $B/hdr
for a in $APPS; do
  for v in b76f3fb fd4b76a; do
    bash $B/start.sh $v $a > /tmp/h.out 2>&1
    sleep 2
    w=$(xdotool getactivewindow)
    echo "$a $v: window \"$(xdotool getwindowname $w)\""
    gnome-screenshot -w -f $B/hdr/$a-$v.png 2>/dev/null
    pkill -x "${a:0:15}"; sleep 1
  done
done
python3 - "$B" $APPS <<'PYEOF'
import sys
from PIL import Image, ImageDraw
b, apps = sys.argv[1], sys.argv[2:]
rows = []
for a in apps:
    strips = []
    for v in ("b76f3fb", "fd4b76a"):
        try:
            im = Image.open(f"{b}/hdr/{a}-{v}.png").convert("RGB")
            im = im.crop((0, 0, min(im.width, 640), min(im.height, 120)))
        except Exception:
            im = Image.new("RGB", (640, 120), "grey")
        canvas = Image.new("RGB", (640, 136), "white")
        canvas.paste(im, (0, 16))
        ImageDraw.Draw(canvas).text((4, 2), f"{a} {v}", fill="black")
        strips.append(canvas)
    row = Image.new("RGB", (1290, 136), "white")
    row.paste(strips[0], (0, 0)); row.paste(strips[1], (650, 0))
    rows.append(row)
out = Image.new("RGB", (1290, 136 * len(rows)), "white")
for i, r in enumerate(rows):
    out.paste(r, (0, 136 * i))
out.save(f"{b}/headers.png")
print("headers.png", out.size)
PYEOF
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
sudo -n cp $B/libgtk-nocsd.so.0.pkg $T.new && sudo -n mv $T.new $T
echo "packaged library restored: $(sha256sum < $T | cut -c1-16)"
