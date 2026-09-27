#!/usr/bin/env python3
"""Small domain wrappers for explicit Git staging and non-forced branch push."""

import argparse
from pathlib import Path
import subprocess
import sys


def run(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], check=check, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--repo", required=True, type=Path)
    stage.add_argument("paths", nargs="+", help="exact repository-relative file paths")
    push = sub.add_parser("push")
    push.add_argument("--repo", required=True, type=Path)
    push.add_argument("--branch", required=True)
    push.add_argument("--remote", default="origin")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not repo.is_dir(): parser.error("repository does not exist")
    if args.operation == "stage":
        exact = []
        for raw in args.paths:
            path = Path(raw)
            if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or any(char in raw for char in "*?[]"):
                parser.error(f"stage requires an exact repository-relative path: {raw}")
            resolved = (repo / path).resolve()
            try: resolved.relative_to(repo)
            except ValueError: parser.error(f"path escapes repository: {raw}")
            if resolved.is_dir(): parser.error(f"directories are not accepted; list the exact files: {raw}")
            exact.append(raw)
        return subprocess.run(["git", "-C", str(repo), "add", "--", *exact], check=False).returncode
    branch = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if branch != args.branch: parser.error(f"current branch is {branch!r}, not requested {args.branch!r}")
    if args.remote != "origin": parser.error("only the configured origin remote is allowed")
    return subprocess.run(["git", "-C", str(repo), "push", "origin", f"HEAD:refs/heads/{branch}"], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
