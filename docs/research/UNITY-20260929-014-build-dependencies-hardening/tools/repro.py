#!/usr/bin/env python3
"""UNITY-20260929-014: reproduce the three code remarks of UNITY-20260929-013
Verifier round 2 against scripts/ of the checkout given as argv[1]:
  R1 build-dependencies/ symlinked out of the manifest's directory is accepted
  R2 a boolean size is accepted (bool is an int)
  R3 extra_packages() leaves a copy behind when it refuses a package
Prints one line per probe: ACCEPTED/LEFT (the defect) or REFUSED/CLEAN."""

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

scripts = Path(sys.argv[1]).resolve() / "scripts"
sys.path.insert(0, str(scripts))


def load(name):
    spec = importlib.util.spec_from_file_location(name, scripts / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bd = load("build_dependencies")
bs = load("build_sbuild")


def make_deb(path, package, version, arch="amd64", source=None):
    root = path.parent / f".root-{path.name}"
    (root / "DEBIAN").mkdir(parents=True)
    control = f"Package: {package}\nVersion: {version}\nArchitecture: {arch}\nMaintainer: t <t@example.com>\nDescription: t\n"
    if source:
        control += f"Source: {source}\n"
    (root / "DEBIAN" / "control").write_text(control)
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(path)],
                   check=True, capture_output=True)
    return path


with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    pool = base / "pool"
    deb = make_deb(pool / "main/n/nux/libnux-4.0-dev_4.0.8-0ubuntu15+unity2_amd64.deb",
                   "libnux-4.0-dev", "4.0.8-0ubuntu15+unity2", source="nux")
    entry = {"file": f"build-dependencies/{deb.name}", "sha256": hashlib.sha256(deb.read_bytes()).hexdigest(),
             "size": deb.stat().st_size, "package": "libnux-4.0-dev", "version": "4.0.8-0ubuntu15+unity2",
             "architecture": "amd64", "source": "nux"}

    # R1: the manifest's build-dependencies/ is a symlink to a directory elsewhere
    out = base / "out1"; out.mkdir()
    elsewhere = base / "elsewhere"; elsewhere.mkdir()
    (elsewhere / deb.name).write_bytes(deb.read_bytes())
    (out / "build-dependencies").symlink_to(elsewhere)
    error = bd.check_entries([entry], out, pool)
    print("R1 symlinked build-dependencies/:", "ACCEPTED" if error is None else f"REFUSED ({error})")

    # R2: size true
    out = base / "out2"; (out / "build-dependencies").mkdir(parents=True)
    (out / "build-dependencies" / deb.name).write_bytes(deb.read_bytes())
    error = bd.check_entries([dict(entry, size=True)], out, pool)
    print("R2 size=True:", "ACCEPTED" if error is None else f"REFUSED ({error})")

    # R3: a refused package (foreign architecture) is still copied
    foreign = make_deb(base / "in/libfoo_1.0_armhf.deb", "libfoo", "1.0", arch="armhf")
    depdir = base / "out3" / "build-dependencies"; depdir.parent.mkdir()
    records, error = bs.extra_packages([str(foreign)], "amd64", depdir)
    left = sorted(p.name for p in depdir.iterdir()) if depdir.exists() else []
    print("R3 refused package:", f"refused={error is not None}", "LEFT " + ",".join(left) if left else "CLEAN")
