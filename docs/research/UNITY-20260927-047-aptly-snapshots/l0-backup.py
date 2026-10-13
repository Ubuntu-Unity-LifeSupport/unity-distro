#!/usr/bin/env python3
"""UNITY-20260927-047 phase L, L0 item 7: back up the live db/ and public/
(cp -a, no aptly process, the database is not opened), write a sha256 list of
both copies and compare it with the live files, and take the live-list
baseline of all of /srv/aptly. Refuses if an aptly process runs.
Usage: l0-backup.py BACKUP_DIR LIVE_LIST_OUT"""

import hashlib
import os
from pathlib import Path
import subprocess
import sys

LIVE = Path("/srv/" + "aptly")
dst, live_out = Path(sys.argv[1]), Path(sys.argv[2])


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def listing(base, parts):
    return {str(p.relative_to(base)): sha(p) for part in parts for p in sorted((base / part).rglob("*"))
            if p.is_file() and not p.is_symlink()}


if subprocess.run(["pidof", "aptly"], capture_output=True).returncode == 0:
    sys.exit("an aptly process is running; no backup")
if dst.exists():
    sys.exit(f"{dst} exists")
os.umask(0o077)
dst.mkdir(parents=True, mode=0o700)
for part in ("db", "public"):
    subprocess.run(["cp", "-a", str(LIVE / part), str(dst / part)], check=True)
live = listing(LIVE, ("db", "public"))
copy = listing(dst, ("db", "public"))
text = "".join(f"{v}  {k}\n" for k, v in sorted(copy.items()))
(dst / "backup.sha256").write_text(text)
print(f"backup {dst}: {len(copy)} files (db+public), equal to live: {copy == live}")
print(f"backup.sha256 sha256: {hashlib.sha256(text.encode()).hexdigest()}")
full = {str(p.relative_to(LIVE)): sha(p) for p in sorted(LIVE.rglob("*")) if p.is_file() and not p.is_symlink()}
ltext = "".join(f"{v}  {k}\n" for k, v in sorted(full.items()))
live_out.write_text(ltext)
print(f"live-list baseline: {len(full)} files, sha256 {hashlib.sha256(ltext.encode()).hexdigest()}")
