#!/usr/bin/env python3
"""Back up the live repository database before repo add / repo remove /
snapshot drop (docs/ENGINEERING-PROCESS.md section 6, steps 3 and 5;
UNITY-20261008-004).

Copies <live>/db only - enough for those steps, which change only db/; not a
backup for publish switch or db cleanup, which change public/ and the pool.
Holds a shared flock on <live>/db/LOCK for the copy and the comparison: a
repository tool call waits meanwhile, and a busy lock means one is working
now, so the backup refuses. Writes db.sha256 and backup.json next to the copy.

Exit 0: complete copy equal to the live db. 1: copy incomplete or different
(left in place). 2: refused, nothing created.
Usage: backup_aptly_db.py [BACKUP_DIR] [--task UNITY-YYYYMMDD-NNN]
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

LIVE = Path("/srv/aptly")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def listing(root):
    """{"db/<path>": sha256} of every regular file under root/db."""
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted((root / "db").rglob("*")) if p.is_file()}


def refuse(message):
    print(f"backup refused: {message}", file=sys.stderr)
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("backup_dir", nargs="?", type=Path,
                        help="new directory for the copy (default ~/backups/<task or aptly-db>-<UTC stamp>)")
    parser.add_argument("--task", help="task id, recorded and used in the default directory name")
    parser.add_argument("--live", type=Path, default=LIVE, help="for tests only: another repository root")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    live = args.live.resolve()
    dst = args.backup_dir or Path.home() / "backups" / f"{args.task or 'aptly-db'}-{now:%Y%m%dT%H%M%SZ}"
    dst = dst.expanduser()
    lock_path = live / "db" / "LOCK"
    if not (live / "db").is_dir() or not lock_path.is_file():
        return refuse(f"no repository database with a LOCK file at {live / 'db'}")
    if dst.exists() or dst.is_symlink():
        return refuse(f"{dst} exists")
    resolved = dst.parent.resolve() / dst.name
    if resolved == live or live in resolved.parents:
        return refuse(f"{dst} lies inside the live repository root {live}")

    with open(lock_path, "rb") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return refuse(f"{lock_path} is locked: a repository tool is working on the database")
        if shutil.which("pidof") is None:
            return refuse("pidof is not available to check for a running repository tool")
        if subprocess.run(["pidof", "aptly"], capture_output=True).returncode == 0:
            return refuse("a repository tool process is running")

        os.umask(0o077)
        dst.mkdir(parents=True, mode=0o700)
        copied = subprocess.run(["cp", "-a", str(live / "db"), str(dst / "db")], capture_output=True, text=True)
        complete = copied.returncode == 0 and (dst / "db").is_dir()
        copy = listing(dst) if (dst / "db").is_dir() else {}
        live_now = listing(live)
    equal = complete and copy == live_now

    text = "".join(f"{digest}  {name}\n" for name, digest in sorted(copy.items()))
    (dst / "db.sha256").write_text(text)
    record = {"schema": 1, "live": str(live), "task": args.task, "created_at": now.isoformat(timespec="seconds"),
              "files": len(copy), "list_sha256": hashlib.sha256(text.encode()).hexdigest(),
              "complete": complete, "equal_to_live": equal}
    if not complete:
        record["cp_error"] = copied.stderr.strip()[-500:]
    (dst / "backup.json").write_text(json.dumps(record, indent=1) + "\n")
    print(f"db backup {dst}: {len(copy)} files, complete: {complete}, equal to live: {equal}, "
          f"list sha256 {record['list_sha256']}")
    if not equal:
        print("backup is NOT usable: " + ("the copy failed" if not complete else "the copy differs from the live db"),
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
