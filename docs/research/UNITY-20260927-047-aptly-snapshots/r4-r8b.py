"""Phase R steps R4 and R8b (UNITY-20260927-047), no aptly process involved.
  backup:  R4  - cp -a state/public and state/db to backup-r4/, sha256 list of
                 both sides compared, list written to backup-r4.sha256
  restore: R8b - move state/public and state/db to aside-r8b/, cp -a the R4
                 backup back, compare every file's sha256 with backup-r4.sha256
Nothing is deleted."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

T = Path("/var/tmp/" + "aptly-rehearsal")
PARTS = ("public", "db")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def listing(base):
    out = {}
    for part in PARTS:
        for p in sorted((base / part).rglob("*")):
            if p.is_file() and not p.is_symlink():
                out[str(p.relative_to(base))] = sha256(p)
    return out


def cp_a(src, dst):
    subprocess.run(["cp", "-a", str(src), str(dst)], check=True)


os.umask(0o077)
mode = sys.argv[1]
if mode == "backup":
    dst = T / "backup-r4"
    if dst.exists():
        sys.exit(f"{dst} exists")
    dst.mkdir(mode=0o700)
    for part in PARTS:
        cp_a(T / "state" / part, dst / part)
    a, b = listing(T / "state"), listing(dst)
    (T / "backup-r4.sha256").write_text("".join(f"{v}  {k}\n" for k, v in sorted(b.items())))
    print(f"R4 backup: {len(b)} files, sha256 equal to state: {a == b}")
elif mode == "restore":
    aside = T / "aside-r8b"
    if aside.exists():
        sys.exit(f"{aside} exists")
    aside.mkdir(mode=0o700)
    for part in PARTS:
        os.rename(T / "state" / part, aside / part)
        cp_a(T / "backup-r4" / part, T / "state" / part)
    want = dict(line.split("  ", 1)[::-1] for line in (T / "backup-r4.sha256").read_text().splitlines())
    got = listing(T / "state")
    print(f"R8b restore: moved state/public+db to aside-r8b; {len(got)} files restored, "
          f"byte-identical to the R4 list: {got == want}")
else:
    sys.exit("usage: backup|restore")
