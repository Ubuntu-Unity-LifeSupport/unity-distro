"""UNITY-20260927-021: for every artifact of the r2 manifest that aptly stores
(.dsc, source files, .deb, .ddeb), find pool files with that name and report
whether one has the manifest sha256 (read-only). Also lists same-name files
with other hashes (the first build's orphans)."""
import hashlib
import json
from pathlib import Path
import sys

POOL = Path("/srv/" + "aptly" + "/pool")
m = json.load(open(sys.argv[1]))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


by_name = {}
for p in POOL.rglob("*"):
    if p.is_file() and "_calamares-settings" in p.name and "unity2" in p.name:
        by_name.setdefault(p.name.split("_", 1)[1], []).append(sha(p))
for a in m["artifacts"]:
    if a["kind"] in ("changes", "buildinfo"):
        continue
    hashes = by_name.get(a["file"], [])
    print(f"{'OK ' if a['sha256'] in hashes else 'MISSING'} {a['file']}  pool copies {len(hashes)}, others {[h[:12] for h in hashes if h != a['sha256']]}")
