#!/usr/bin/env python3
"""Append one complete decision/patch entry under an exclusive file lock."""

import argparse
import fcntl
from pathlib import Path

ROOT = Path.home() / "unity-distro"
TARGETS = {"decisions": ROOT / "docs/DECISIONS.md", "patches": ROOT / "docs/PATCHES.md"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", choices=TARGETS)
    parser.add_argument("entry", type=Path, help="UTF-8 file containing the complete new section")
    args = parser.parse_args()
    text = args.entry.read_text(encoding="utf-8").strip()
    if not text: parser.error("entry file is empty")
    target = TARGETS[args.record]
    if not target.is_file(): parser.error(f"shared base record does not exist: {target}")
    lock_dir = Path.home() / ".cache/unity-distro/locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{args.record}.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with target.open("a+", encoding="utf-8") as stream:
            stream.seek(0, 2)
            stream.write("\n\n" + text + "\n")
            stream.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
