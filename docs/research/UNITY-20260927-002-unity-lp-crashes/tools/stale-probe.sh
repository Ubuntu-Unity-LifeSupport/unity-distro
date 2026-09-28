#!/bin/bash
# UNITY-20260927-002 (agent A): run shaped-stale and screenshot each phase;
# report, for the window's area plus a shadow margin (x 250-570, y 250-510),
# how many pixels differ by more than 24 (any channel) from phase 0 (nothing
# mapped). Screenshots in ~/stale/<label>/.
. ~/envt.sh
L=${1:-run}; O=~/stale/$L; mkdir -p $O
~/shaped-stale 4 > $O/phases.txt &
P=$!
for n in 0 1 2 3; do sleep 2; gnome-screenshot -f $O/phase$n.png 2>/dev/null; sleep 2; done
wait $P
python3 - "$O" <<'PY'
import sys
from PIL import Image, ImageChops
o = sys.argv[1]
box = (250, 250, 570, 510)
base = Image.open(f"{o}/phase0.png").convert("RGB").crop(box)
for n in (1, 2, 3):
    img = Image.open(f"{o}/phase{n}.png").convert("RGB").crop(box)
    diff = ImageChops.difference(base, img)
    changed = sum(1 for px in diff.getdata() if max(px) > 24)
    bbox = diff.point(lambda v: 255 if v > 24 else 0).getbbox()
    print(f"phase {n}: {changed} pixels differ from phase 0; changed box {bbox}")
PY
