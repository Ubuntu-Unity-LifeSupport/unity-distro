#!/usr/bin/env python3
"""abicompare.py OLD_DIR NEW_DIR - UNITY-20260927-028: compare two builds of hud.

For every .deb present in both directories (matched by package name): the file
list, and for every shared library (*.so.*) and every executable the dynamic
symbols it defines (nm -D --defined-only, demangled), and whether the file's
contents differ at all. .ddeb debug packages are skipped."""
import os
import subprocess
import sys
import tempfile


def debs(d):
    out = {}
    for f in os.listdir(d):
        if f.endswith(".deb"):
            out[f.split("_")[0]] = os.path.join(d, f)
    return out


def extract(deb, dest):
    subprocess.run(["dpkg-deb", "-x", deb, dest], check=True)
    files = []
    for root, _, names in os.walk(dest):
        for n in names:
            files.append(os.path.relpath(os.path.join(root, n), dest))
    return sorted(files)


def symbols(path):
    r = subprocess.run(["nm", "-D", "--defined-only", "-C", path], capture_output=True, text=True)
    return sorted({" ".join(l.split()[1:]) for l in r.stdout.splitlines() if l.strip()})


def is_elf(path):
    with open(path, "rb") as f:
        return f.read(4) == b"\x7fELF"


old, new = debs(sys.argv[1]), debs(sys.argv[2])
total_sym_diff = 0
for pkg in sorted(set(old) | set(new)):
    if pkg not in old or pkg not in new:
        print(f"{pkg}: only in {'old' if pkg in old else 'new'}")
        continue
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        fa, fb = extract(old[pkg], a), extract(new[pkg], b)
        if fa != fb:
            print(f"{pkg}: FILE LISTS DIFFER: -{sorted(set(fa) - set(fb))} +{sorted(set(fb) - set(fa))}")
        changed, elf_sym = [], []
        for f in fa:
            pa, pb = os.path.join(a, f), os.path.join(b, f)
            if os.path.islink(pa) or not os.path.isfile(pb):
                continue
            same = open(pa, "rb").read() == open(pb, "rb").read()
            if not same:
                changed.append(f)
            if is_elf(pa):
                sa, sb = symbols(pa), symbols(pb)
                d = len(set(sa) ^ set(sb))
                total_sym_diff += d
                elf_sym.append(f"{f} ({len(sa)} symbols, {'identical' if d == 0 else f'{d} differ: ' + str(sorted(set(sa) ^ set(sb))[:6])})")
        print(f"{pkg}: {len(fa)} files, file list {'identical' if fa == fb else 'DIFFERS'}, contents differ in {len(changed)}")
        for e in elf_sym:
            print(f"   ELF {e}")
        for c in changed:
            print(f"   changed: {c}")
print(f"TOTAL dynamic-symbol differences: {total_sym_diff}")
