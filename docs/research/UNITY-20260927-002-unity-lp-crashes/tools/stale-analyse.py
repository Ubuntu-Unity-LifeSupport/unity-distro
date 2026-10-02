#!/usr/bin/env python3
"""UNITY-20260927-002 (agent A): compare the phase screenshots of
stale-probe.sh against phase 0 at several thresholds.
usage: stale-analyse.py DIR [THRESHOLD ...]"""
import sys
from PIL import Image, ImageChops
o = sys.argv[1]
thresholds = [int(t) for t in sys.argv[2:]] or [2, 4, 8, 24]
box = (250, 250, 570, 510)   # window 300,300 200x150 plus a 50 px margin
base = Image.open(f"{o}/phase0.png").convert("RGB").crop(box)
for thr in thresholds:
    for n in (1, 2, 3):
        diff = ImageChops.difference(base, Image.open(f"{o}/phase{n}.png").convert("RGB").crop(box))
        mask = diff.convert("L").point(lambda v: 255 if v > thr else 0)
        count = sum(1 for p in mask.get_flattened_data() if p) if hasattr(mask, "get_flattened_data") else sum(1 for p in mask.getdata() if p)
        print(f"threshold {thr:2} phase {n}: {count:6} pixels changed, box {mask.getbbox()}")
