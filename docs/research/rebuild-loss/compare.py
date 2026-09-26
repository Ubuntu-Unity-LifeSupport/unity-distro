#!/usr/bin/python3
"""compare.py SRC ARCHDIR OUTDIR - per binary package, files in the archive
.deb missing from the rebuild (LOST) and new ones (NEW); doc/changelog and
.build-id noise ignored; risky classes marked with !"""
import sys, subprocess, glob, os, re
src, adir, odir = sys.argv[1:4]
RISK = re.compile(r'systemd/(user|system)/|dbus-1/services/|xdg/autostart/|glib-2\.0/schemas/')
NOISE = re.compile(r'^/usr/share/doc/|/\.build-id/|^/usr/lib/debug/')
def files(deb):
    out = subprocess.run(['dpkg-deb', '-c', deb], capture_output=True, text=True).stdout
    s = set()
    for l in out.splitlines():
        p = l.split(None, 5)[-1].split(' -> ')[0]
        p = p[1:] if p.startswith('.') else p
        if p.endswith('/') or NOISE.search(p):
            continue
        s.add(p)
    return s
def name(deb): return os.path.basename(deb).split('_')[0]
arch = {name(d): d for d in glob.glob(adir + '/*.deb')}
new = {name(d): d for d in glob.glob(odir + '/*.deb') if not name(d).endswith('-dbgsym')}
total_lost = 0
for b in sorted(arch):
    if b not in new:
        print('%s: %s NOT BUILT by the rebuild' % (src, b)); total_lost += 1; continue
    a, n = files(arch[b]), files(new[b])
    lost, added = sorted(a - n), sorted(n - a)
    for p in lost:
        print('%s: %s LOST %s%s' % (src, b, '! ' if RISK.search(p) else '', p)); total_lost += 1
    for p in added:
        print('%s: %s NEW  %s' % (src, b, p))
if total_lost == 0:
    print('%s: no file lost (%d packages)' % (src, len(arch)))
