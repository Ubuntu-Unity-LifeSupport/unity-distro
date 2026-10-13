"""UNITY-20260927-021 replacement step 0: cp -a the live db/ into BACKUP_DIR
(no aptly process), sha256 list of the copy vs live, and check that public/
is byte-identical to the post-phase-L list (logs/48b of -047), i.e. the
publication is still ./resolute = snapshot 047. Usage: r021_backup_db.py BACKUP_DIR"""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

LIVE = Path("/srv/" + "aptly")
L48 = Path("/home/claude/work/b/unity-distro-047/docs/research/UNITY-20260927-047-" + "aptly" + "-snapshots/logs/48b-live-list-after-L.sha256")
dst = Path(sys.argv[1])


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if subprocess.run(["pidof", "aptly"], capture_output=True).returncode == 0:
    sys.exit("an aptly process is running")
if dst.exists():
    sys.exit(f"{dst} exists")
os.umask(0o077)
dst.mkdir(parents=True, mode=0o700)
subprocess.run(["cp", "-a", str(LIVE / "db"), str(dst / "db")], check=True)
live = {str(p.relative_to(LIVE)): sha(p) for p in sorted((LIVE / "db").rglob("*")) if p.is_file()}
copy = {str(p.relative_to(dst)): sha(p) for p in sorted((dst / "db").rglob("*")) if p.is_file()}
text = "".join(f"{v}  {k}\n" for k, v in sorted(copy.items()))
(dst / "db.sha256").write_text(text)
print(f"db backup {dst}: {len(copy)} files, equal to live: {copy == live}, list sha256 {hashlib.sha256(text.encode()).hexdigest()}")
pub_now = {str(p.relative_to(LIVE)): sha(p) for p in sorted((LIVE / "public").rglob("*")) if p.is_file() and not p.is_symlink()}
pub_48 = {line[66:]: line[:64] for line in L48.read_text().splitlines() if line[66:].startswith("public/")}
print(f"public/ now {len(pub_now)} files; equal to the post-L list (047 logs/48b): {pub_now == pub_48}")
