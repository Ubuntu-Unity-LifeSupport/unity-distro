#!/usr/bin/env python3
"""UNITY-20260927-027: binary compatibility of the gated libnux-4.0-0 +unity3 with the
published +unity2 that unity +unity12 was built against (UNITY-20260927-040).

For every shared library in the package: SONAME, exported dynamic symbols
(defined, with version and type), and NEEDED. Also the package's shlibs and
symbols control files. Usage: abi-compare.py <old.deb> <new.deb>
"""
import subprocess
import sys
import tempfile
from pathlib import Path


def unpack(deb, into):
    subprocess.run(["dpkg-deb", "-R", deb, into], check=True)
    return Path(into)


def elf_info(path):
    dyn = subprocess.run(["readelf", "-dW", str(path)], check=True, capture_output=True, text=True).stdout
    soname = [l.split("[")[1].rstrip("]") for l in dyn.splitlines() if "(SONAME)" in l]
    needed = sorted(l.split("[")[1].rstrip("]") for l in dyn.splitlines() if "(NEEDED)" in l)
    syms = subprocess.run(["nm", "-D", "--defined-only", "--with-symbol-versions", str(path)],
                          check=True, capture_output=True, text=True).stdout
    exported = sorted(" ".join(l.split()[1:]) for l in syms.splitlines() if l.strip())
    return soname, needed, exported


old, new = sys.argv[1], sys.argv[2]
with tempfile.TemporaryDirectory() as t:
    a, b = unpack(old, f"{t}/old"), unpack(new, f"{t}/new")
    libs = sorted(p.relative_to(b) for p in b.rglob("*.so.*") if p.is_file() and not p.is_symlink())
    for rel in libs:
        so_a, need_a, exp_a = elf_info(a / rel) if (a / rel).exists() else ([], [], [])
        so_b, need_b, exp_b = elf_info(b / rel)
        removed = sorted(set(exp_a) - set(exp_b))
        added = sorted(set(exp_b) - set(exp_a))
        print(f"{rel}: SONAME {so_a} -> {so_b}; exported {len(exp_a)} -> {len(exp_b)}; "
              f"removed {len(removed)}, added {len(added)}; NEEDED {'same' if need_a == need_b else f'{need_a} -> {need_b}'}")
        for s in removed[:20]:
            print("   - " + s)
        for s in added[:20]:
            print("   + " + s)
    for ctl in ("shlibs", "symbols"):
        fa, fb = a / "DEBIAN" / ctl, b / "DEBIAN" / ctl
        if fa.exists() or fb.exists():
            same = fa.exists() and fb.exists() and fa.read_text().replace("unity2", "X") == fb.read_text().replace("unity3", "X")
            print(f"DEBIAN/{ctl}: {'same apart from the version' if same else 'DIFFERS'}")
            if not same and fb.exists():
                print("   new: " + fb.read_text().strip().replace("\n", " | ")[:300])
                if fa.exists():
                    print("   old: " + fa.read_text().strip().replace("\n", " | ")[:300])
