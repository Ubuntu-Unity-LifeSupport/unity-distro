#!/usr/bin/env python3
"""Build the checked-out source with sbuild and emit artifact-hash provenance."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def run(args, cwd=None, check=True, capture=True):
    return subprocess.run(args, cwd=cwd, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--target-series", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    repo = args.source_repo.resolve()
    output = args.output_dir.resolve()
    if not repo.is_dir():
        parser.error("source repository must exist")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        parser.error("use a fresh empty output directory for each build")
    if not args.task_id.startswith("UNITY-"):
        parser.error("task ID must use the UNITY-YYYYMMDD-NNN format")
    status = run(["git", "-C", str(repo), "status", "--porcelain"]).stdout
    if status.strip():
        parser.error("source repository must be clean before building")
    commit = run(["git", "-C", str(repo), "rev-parse", "HEAD"]).stdout.strip()
    tree = run(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"]).stdout.strip()
    version = run(["dpkg-parsechangelog", "-S", "Version"], cwd=repo).stdout.strip()
    package = run(["dpkg-parsechangelog", "-S", "Source"], cwd=repo).stdout.strip()
    started = datetime.now(timezone.utc)
    command = ["sbuild", "-d", args.target_series, "--no-clean-source"]
    logfile = output / f"{args.task_id}-{package}-{version}-sbuild.log"
    with logfile.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(command) + "\n")
        result = subprocess.run(command, cwd=repo, text=True, stdout=log, stderr=subprocess.STDOUT, check=False)
    finished = datetime.now(timezone.utc)
    if result.returncode:
        print(f"sbuild failed ({result.returncode}); see {logfile}", file=sys.stderr)
        return result.returncode
    # sbuild puts result files next to the source tree by default. Capture only
    # artifacts matching the package and version produced during this run.
    search_roots = {repo.parent, output}
    candidates = []
    for root in search_roots:
        candidates.extend(p for p in root.glob("*") if p.is_file() and p.suffix in {".deb", ".dsc", ".changes", ".buildinfo", ".udeb"})
    artifacts = []
    for path in sorted(set(candidates)):
        if package not in path.name or version not in path.name:
            continue
        if path.stat().st_mtime < started.timestamp() - 2:
            continue
        copied = output / path.name
        if path.resolve() != copied.resolve():
            copied.write_bytes(path.read_bytes())
            path = copied
        item = {"file": path.name, "sha256": sha256(path), "size": path.stat().st_size}
        if path.suffix == ".deb":
            item.update({"kind": "binary", "package": run(["dpkg-deb", "-f", str(path), "Package"]).stdout.strip(),
                         "version": run(["dpkg-deb", "-f", str(path), "Version"]).stdout.strip(),
                         "architecture": run(["dpkg-deb", "-f", str(path), "Architecture"]).stdout.strip()})
        elif path.suffix == ".dsc":
            item.update({"kind": "source", "package": package, "version": version})
        else:
            item["kind"] = path.suffix.lstrip(".")
        artifacts.append(item)
    if not any(item["kind"] == "source" for item in artifacts) or not any(item["kind"] == "binary" for item in artifacts):
        print("sbuild succeeded but matching source and binary artifacts were not both found", file=sys.stderr)
        return 2
    manifest = {
        "schema": 1, "task_id": args.task_id, "package": package,
        "candidate_version": version, "target_series": args.target_series,
        "source_repo": str(repo), "source_commit": commit,
        "source_tree_hash": tree, "build_command": command,
        "build_started": started.isoformat(), "build_finished": finished.isoformat(),
        "result": "PASS", "log": {"file": logfile.name, "sha256": sha256(logfile)},
        "artifacts": artifacts,
    }
    manifest_path = output / f"{args.task_id}-{package}-build-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
