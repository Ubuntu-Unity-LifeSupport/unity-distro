"""UNITY-20260927-021 VERIFYING: file lists and changelog entries of the gated
+unity2 binaries against the published +unity1 in the live pool (read-only).
Usage: r021_filelists.py BUILD_DIR"""
import glob
import gzip
import os
import subprocess
import sys
import tempfile

POOL = "/srv/" + "aptly" + "/public/pool"
build = sys.argv[1]


def files(deb):
    out = subprocess.run(["dpkg-deb", "-c", deb], capture_output=True, text=True, check=True).stdout
    return sorted(" ".join([l.split()[0], l.split(None, 5)[5]]) for l in out.splitlines())


def changelog_entries(deb, pkg):
    with tempfile.TemporaryDirectory() as t:
        subprocess.run(["dpkg-deb", "-x", deb, t], check=True)
        p = os.path.join(t, "usr/share/doc", pkg, "changelog.Debian.gz")
        if not os.path.lexists(p):
            p = os.path.join(t, "usr/share/doc", pkg, "changelog.gz")
        if os.path.islink(p):
            return f"symlink -> {os.readlink(p)}"
        if not os.path.exists(p):
            return "absent"
        text = gzip.open(p, "rt", errors="replace").read()
        return sum(1 for line in text.splitlines() if line and not line[0].isspace() and "(" in line and ")" in line)


for pkg in ("calamares-settings-ubuntu-unity", "calamares-settings-ubuntu-common", "calamares-settings-ubuntu-common-data"):
    new = glob.glob(f"{build}/{pkg}_26.04.12+unity2_*.deb")[0]
    old = glob.glob(f"{POOL}/**/{pkg}_26.04.12+unity1_*.deb", recursive=True)
    if not old:
        print(pkg, "no +unity1 in pool")
        continue
    a, b = files(old[0]), files(new)
    added, removed = sorted(set(b) - set(a)), sorted(set(a) - set(b))
    print(f"{pkg}: +unity1 {len(a)} entries, +unity2 {len(b)}; added {added}; removed {removed}")
    print(f"  changelog entries: +unity1 {changelog_entries(old[0], pkg)}, +unity2 {changelog_entries(new, pkg)}")
