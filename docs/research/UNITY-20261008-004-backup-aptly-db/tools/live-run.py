#!/usr/bin/env python3
"""UNITY-20261008-004: the one live run approved by C (2026-10-08, slot closed).
Records the live root's file list with size and mtime before and after one run
of scripts/backup_aptly_db.py, and the newest db file, and compares them; the
backup's sha256 list is compared with the live db read afterwards.
Usage: live-run.py <worktree>"""
import hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

LIVE = Path("/srv/" + "aptly")
wt = Path(sys.argv[1]).resolve()

def state():
    out = {}
    for p in sorted(LIVE.rglob("*")):
        try:
            st = p.lstat()
        except FileNotFoundError:
            continue
        out[str(p.relative_to(LIVE))] = (st.st_size, st.st_mtime_ns)
    return out

def newest_db():
    p = max((q for q in (LIVE / "db").iterdir() if q.is_file()), key=lambda q: q.stat().st_mtime_ns)
    return p.name, datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")

before, nb = state(), newest_db()
print("newest db file before:", *nb)
r = subprocess.run([sys.executable, str(wt / "scripts/backup_aptly_db.py"), "--task", "UNITY-20261008-004"],
                   capture_output=True, text=True)
print("rc", r.returncode)
print("stdout:", r.stdout.strip())
print("stderr:", r.stderr.strip() or "-")
after, na = state(), newest_db()
print("newest db file after:", *na, "| unchanged:", na == nb)
changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
print("files under the live root changed/added/removed:", len(changed), changed[:10])
dst = Path(r.stdout.split("db backup ", 1)[1].split(":", 1)[0]) if "db backup " in r.stdout else None
if dst:
    record = json.loads((dst / "backup.json").read_text())
    live_list = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(LIVE).as_posix()}\n"
                        for p in sorted((LIVE / "db").rglob("*")) if p.is_file())
    print("backup:", dst, "mode", oct(dst.stat().st_mode & 0o777))
    print("backup.json:", json.dumps({k: record[k] for k in ("files", "list_sha256", "complete", "equal_to_live")}))
    print("db.sha256 equals the live db listed again now:", (dst / "db.sha256").read_text() == live_list)
