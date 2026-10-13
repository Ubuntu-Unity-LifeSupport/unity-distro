"""Read-only: per-file sha256 list of the live repository root, its sha256, and
the newest mtime/ctime of any entry (UNITY-20260927-047 pre-R baseline).
Usage: live_list.py OUTFILE (OUTFILE outside the live root)."""
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/srv/" + "aptly")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


entries = sorted(ROOT.rglob("*"))
files = [p for p in entries if p.is_file() and not p.is_symlink()]
text = "".join(f"{sha256(p)}  {p.relative_to(ROOT)}\n" for p in files)
Path(sys.argv[1]).write_text(text)
newest_m = max(entries + [ROOT], key=lambda p: os.lstat(p).st_mtime)
newest_c = max(entries + [ROOT], key=lambda p: os.lstat(p).st_ctime)
ts = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(f"files {len(files)}, entries {len(entries)}")
print(f"list sha256 (sha256sum format, sorted by path): {hashlib.sha256(text.encode()).hexdigest()}")
print(f"newest mtime {ts(os.lstat(newest_m).st_mtime)} {newest_m.relative_to(ROOT) if newest_m != ROOT else '.'}")
print(f"newest ctime {ts(os.lstat(newest_c).st_ctime)} {newest_c.relative_to(ROOT) if newest_c != ROOT else '.'}")
