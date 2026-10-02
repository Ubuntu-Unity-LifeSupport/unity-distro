#!/usr/bin/env python3
"""UNITY-20260927-012 (copied from UNITY-20260927-040), before repo add: cp -a the live repository db/ into
BACKUP_DIR (no repository tool process running), write the sha256 list of the
copy and compare it with the live db. Same method as UNITY-20260927-021's
replace-backup-db.py. Usage: backup-db.py BACKUP_DIR"""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

LIVE = Path("/srv/" + "aptly")
dst = Path(sys.argv[1])


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if subprocess.run(["pidof", "aptly"], capture_output=True).returncode == 0:
    sys.exit("a repository tool process is running")
if dst.exists():
    sys.exit(f"{dst} exists")
os.umask(0o077)
dst.mkdir(parents=True, mode=0o700)
subprocess.run(["cp", "-a", str(LIVE / "db"), str(dst / "db")], check=True)
live = {str(p.relative_to(LIVE)): sha(p) for p in sorted((LIVE / "db").rglob("*")) if p.is_file()}
copy = {str(p.relative_to(dst)): sha(p) for p in sorted((dst / "db").rglob("*")) if p.is_file()}
text = "".join(f"{v}  {k}\n" for k, v in sorted(copy.items()))
(dst / "db.sha256").write_text(text)
print(f"db backup {dst}: {len(copy)} files, equal to live: {copy == live}, "
      f"list sha256 {hashlib.sha256(text.encode()).hexdigest()}")
