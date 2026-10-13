#!/usr/bin/env python3
"""hudsub.py RAW... - in a dbus-monitor capture of menutrace.sh (it records method calls and signals of
org.gtk.Menus, com.canonical.Unity.WindowStack and com.canonical.hud, but no method returns): per sender, the
org.gtk.Menus Start calls on the LibreOffice menubar, as seconds relative to the HUD StartQuery (negative =
before it); the WindowCreated of the Writer window and the first Changed from LibreOffice, on the same scale."""
import re
import sys
from collections import OrderedDict

HDR = re.compile(r'^(signal|method call) time=(\d+\.\d+) sender=(\S+) -> destination=(\(null destination\)|\S+)'
                 r' serial=\d+ path=([^;]+); interface=([^;]+); member=(\S+)')
menubar = re.compile(r'/org/libreoffice/window/(\d+)/menus/menubar')
for raw in sys.argv[1:]:
    msgs = [m.groups() for m in map(HDR.match, open(raw, errors='replace')) if m]
    q = next((x for x in msgs if x[6] == 'StartQuery'), None)
    if q is None:
        print(f"{raw}: no StartQuery"); continue
    t0 = float(q[1])
    rel = lambda x: round(float(x[1]) - t0, 2)
    starts = OrderedDict()
    xid = None
    for x in msgs:
        mb = menubar.fullmatch(x[4])
        if x[0] == 'method call' and x[6] == 'Start' and mb:
            xid = mb.group(1)
            starts.setdefault(x[2], []).append(rel(x))
    changed = [rel(x) for x in msgs if x[0] == 'signal' and x[6] == 'Changed' and menubar.fullmatch(x[4])]
    created = [rel(x) for x in msgs if x[6] == 'WindowCreated']
    print(f"{raw.split('/')[-1]}: WindowCreated at {created}; first Changed at {changed[0] if changed else '-'}; StartQuery from {q[2]} at 0")
    for sender, ts in starts.items():
        print(f"   {sender}: Start x{len(ts)}, first {ts[0]}, last {ts[-1]}, after the query: {[t for t in ts if t >= 0][:4]}")
