#!/usr/bin/env python3
"""UNITY-20260927-041: compare the gated +unity3 build with +unity2 (UNITY-20260927-021 build-r2).

For every .deb/.ddeb: file list with mode and owner (dates ignored), and for the
three flavour packages the entries of etc/calamares/oemconfig.tar.gz (mode,
owner, size; dates ignored). Also counts the shipped changelog entries.
Usage: compare-builds.py <new build dir> <old build dir>
"""
import gzip
import io
from pathlib import Path
import subprocess
import sys
import tarfile

new, old = Path(sys.argv[1]), Path(sys.argv[2])


def listing(deb):
    out = subprocess.run(["dpkg-deb", "-c", str(deb)], check=True, capture_output=True, text=True).stdout
    rows = set()
    for line in out.splitlines():
        f = line.split()
        rows.add((f[0], f[1], f[-1] if "->" not in f else " ".join(f[5:])))
    return rows


def member(deb, path):
    data = subprocess.run(["dpkg-deb", "--fsys-tarfile", str(deb)], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        return t.extractfile(t.getmember(path)).read()


def oem_entries(deb):
    blob = member(deb, "./etc/calamares/oemconfig.tar.gz")
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
        return {m.name: (oct(m.mode), m.uname or str(m.uid), m.gname or str(m.gid), m.size) for m in t.getmembers()}


def key(p):
    return p.name.split("_", 1)[0] + "_" + p.name.rsplit("_", 1)[-1]


olds = {key(p): p for p in old.iterdir() if p.suffix in (".deb", ".ddeb")}
for p in sorted(q for q in new.iterdir() if q.suffix in (".deb", ".ddeb")):
    o = olds.get(key(p))
    if not o:
        print(f"NEW-ONLY {p.name}")
        continue
    a, b = listing(o), listing(p)
    print(f"{p.name}: file list {'SAME' if a == b else 'DIFF'} as {o.name}")
    for row in sorted(a ^ b):
        print(f"   {'-' if row in a else '+'} {row}")
    if p.name.startswith(("calamares-settings-ubuntu-unity_", "calamares-settings-kubuntu_", "calamares-settings-lubuntu_")):
        ea, eb = oem_entries(o), oem_entries(p)
        diff = sorted(n for n in set(ea) | set(eb) if ea.get(n) != eb.get(n))
        print(f"   oemconfig.tar.gz entries: {len(eb)}, changed vs +unity2: {len(diff)}")
        for n in diff:
            print(f"     {n}: {ea.get(n)} -> {eb.get(n)}")
        for n, v in sorted(eb.items()):
            if n.endswith("sudoers.oem"):
                print(f"     {n} = {v}")
    for doc in ("./usr/share/doc/calamares-settings-ubuntu-common/changelog.gz",):
        try:
            text = gzip.decompress(member(p, doc)).decode()
            print(f"   changelog entries: {sum(1 for l in text.splitlines() if l.startswith('calamares-settings-ubuntu ('))}, top: {text.splitlines()[0]}")
        except KeyError:
            pass
