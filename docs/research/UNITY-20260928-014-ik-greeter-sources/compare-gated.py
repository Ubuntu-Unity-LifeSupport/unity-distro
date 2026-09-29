#!/usr/bin/env python3
"""UNITY-20260928-014: the gated build (pinned chroot) against the tested build.

For the .deb: file list with mode/owner and the sha256 of every regular file in
the data archive. For the .buildinfo: Installed-Build-Depends, what differs.
Usage: compare-gated.py <gated dir> <tested dir>
"""
import hashlib
import io
from pathlib import Path
import re
import subprocess
import sys
import tarfile

gated, tested = Path(sys.argv[1]), Path(sys.argv[2])


def payload(deb):
    data = subprocess.run(["dpkg-deb", "--fsys-tarfile", str(deb)], check=True, capture_output=True).stdout
    out = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        for m in t.getmembers():
            digest = hashlib.sha256(t.extractfile(m).read()).hexdigest() if m.isfile() else m.linkname
            out[m.name] = (oct(m.mode), m.uname, m.gname, digest)
    return out


def build_depends(buildinfo):
    text = buildinfo.read_text()
    block = re.search(r"^Installed-Build-Depends:\n((?: .*\n?)*)", text, re.M).group(1)
    return {m.group(1): m.group(2) for m in re.finditer(r"^\s*([^\s(]+) \(= ([^)]+)\)", block, re.M)}


deb = lambda d: next(p for p in d.glob("indicator-keyboard_*_amd64.deb"))
a, b = payload(deb(tested)), payload(deb(gated))
print(f"deb payload: {len(b)} entries; differ from the tested build: {sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))}")
bi = lambda d: next(p for p in d.glob("indicator-keyboard_*_amd64.buildinfo"))
x, y = build_depends(bi(tested)), build_depends(bi(gated))
changed = sorted(n for n in set(x) | set(y) if x.get(n) != y.get(n))
print(f"Installed-Build-Depends: tested {len(x)}, gated {len(y)}, differing {len(changed)}")
for n in changed:
    print(f"  {n}: {x.get(n, '-')} -> {y.get(n, '-')}")
