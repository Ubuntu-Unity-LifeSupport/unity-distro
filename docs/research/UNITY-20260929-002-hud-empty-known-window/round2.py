#!/usr/bin/env python3
"""round2.py DIR - per boot of logs/02-menutrace: the Writer window, the application id the window stack gives it
(the -029 fallback is the window number), the WindowCreated signals (window id, application id) in the bus
trace, the first org.gtk.Menus Start on the menubar and the first Changed (seconds after START), and the two
HUD answers (menutrace's query, lowindows' query)."""
import glob
import os
import re
import sys

for path in sorted(glob.glob(os.path.join(sys.argv[1], 'boot-*.txt')), key=lambda p: int(re.findall(r'\d+', p)[-1])):
    text = open(path).read()
    start = float(re.search(r'^(\d+\.\d+) START', text, re.M).group(1))
    xid = re.search(r'^\d+\.\d+ XID (\d+)', text, re.M).group(1)
    hud1 = re.search(r'HUD answered=(\d+)', text).group(1)
    m = re.search(r'== HUD query for the focused window\n(\d+)', text)
    hud2 = m.group(1) if m else '?'
    stack = re.search(r'\(%s, \'([^\']*)\', (true|false)' % xid, text)
    created = re.findall(r'time=(\d+\.\d+).*member=WindowCreated\n\s+\d+:\s+uint32 (\d+)\n\s+\d+:\s+string "([^"]*)"', text)
    created = [(round(float(t) - start, 2), w, a) for t, w, a in created]
    first_start = re.search(r'time=(\d+\.\d+) sender=(\S+) -> destination=\S+ serial=\d+ path=/org/libreoffice/window/%s/menus/menubar; interface=org.gtk.Menus; member=Start' % xid, text)
    first_changed = re.search(r'time=(\d+\.\d+) sender=\S+ -> destination=\S+ serial=\d+ path=/org/libreoffice/window/%s/menus/menubar; interface=org.gtk.Menus; member=Changed' % xid, text)
    print(f"{os.path.basename(path)}: xid {xid} app_id {stack.group(1) if stack else '?'} focused {stack.group(2) if stack else '?'} "
          f"HUD {hud1} then {hud2}")
    print(f"   WindowCreated {created}")
    print(f"   first Start on the menubar +{round(float(first_start.group(1)) - start, 2) if first_start else '-'} by {first_start.group(2) if first_start else '-'}, "
          f"first Changed +{round(float(first_changed.group(1)) - start, 2) if first_changed else '-'}")
