#!/usr/bin/env python3
"""UNITY-20260927-004: resolve the raw addresses of a stack printed by
tools/ld-sigterm-trace.bt for session-child PID, using the maps saved at
/var/tmp/ldmaps.PID and gdb with the installed debug info (libc6-dbg,
lightdm-dbgsym). Run as root on target. Usage: symbolize.py PID ADDR..."""
import os, subprocess, sys

pid, addrs = sys.argv[1], sys.argv[2:]
maps = []
for line in open(f"/var/tmp/ldmaps.{pid}"):
    f = line.split()
    if len(f) >= 6:
        start, end = (int(x, 16) for x in f[0].split("-"))
        maps.append((start, end, int(f[2], 16), f[5]))
for a in addrs:
    v = int(a, 16)
    hit = next((m for m in maps if m[0] <= v < m[1]), None)
    if not hit:
        print(a, "?")
        continue
    start, _, off, path = hit
    rel = v - start + off
    out = subprocess.run(["gdb", "-q", "-batch", "-ex", f"info symbol {rel:#x}",
                          "-ex", f"info line *{rel:#x}", path],
                         capture_output=True, text=True).stdout
    print(f"{a} {os.path.basename(path)}+{rel:#x}: " + " | ".join(l.strip() for l in out.splitlines() if l.strip())[:220])
