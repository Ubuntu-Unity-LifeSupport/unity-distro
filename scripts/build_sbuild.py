#!/usr/bin/env python3
"""Build the checked-out source with sbuild and emit artifact-hash provenance."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile


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


# Version-control metadata that must never be in a source package we build.
VCS_NAMES = {".git", ".svn", ".hg", ".bzr", "CVS", "_darcs", "_MTN", "RCS"}


def source_paths(path):
    """Paths inside a source file produced by this build: the '+++' paths of
    a .diff.gz, the members of a tarball. Raises on anything unreadable."""
    if path.name.endswith(".diff.gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
            return [line[4:].split("\t", 1)[0].rstrip("\n") for line in stream if line.startswith("+++ ")]
    with tarfile.open(path) as archive:
        return archive.getnames()


def vcs_entries(dsc_dir, names):
    """UNITY-20260928-007: every VCS path in the source files this build made.
    Orig tarballs (and their signatures) are upstream's, pinned by the .dsc's
    sha256, and not produced from the checkout, so they are not inspected."""
    found = []
    for name in names:
        if ".orig." in name or ".orig-" in name or name.endswith(".asc"):
            continue
        for member in source_paths(dsc_dir / name):
            if VCS_NAMES & set(member.split("/")):
                found.append(f"{name}: {member}")
    return found


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
    # sbuild prints its build log to stdout only when stdout is a terminal or
    # --verbose is given; otherwise the log goes to its own .build file only.
    # UNITY-20260928-007: sbuild builds the source package from this checkout
    # with dpkg-source. Format 3.0 ignores VCS metadata by default, format 1.0
    # does not (.git is diffed, or tarred for full tarballs): -i and -I apply
    # dpkg-source's default ignore lists to every format.
    command = ["sbuild", "-d", args.target_series, "--no-clean-source", "--verbose",
               "--dpkg-source-opt=-i", "--dpkg-source-opt=-I"]
    logfile = output / f"{args.task_id}-{package}-{version}-sbuild.log"
    with logfile.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(command) + "\n")
        log.flush()
        result = subprocess.run(command, cwd=repo, text=True, stdout=log, stderr=subprocess.STDOUT, check=False)
    finished = datetime.now(timezone.utc)
    if result.returncode:
        print(f"sbuild failed ({result.returncode}); see {logfile}", file=sys.stderr)
        return result.returncode
    # sbuild puts result files next to the source tree by default. The .changes
    # of this run lists every binary it produced; the source package is the
    # .dsc. Debian file names carry the version without its epoch.
    file_version = version.split(":", 1)[-1]
    search_roots = [repo.parent, output]
    def fresh(pattern):
        found = {p.resolve() for root in search_roots for p in root.glob(pattern)
                 if p.is_file() and p.stat().st_mtime >= started.timestamp() - 2}
        return sorted(found)
    changes = fresh(f"{package}_{file_version}_*.changes")
    dscs = fresh(f"{package}_{file_version}.dsc")
    if len(changes) != 1 or len(dscs) != 1:
        print(f"expected one .changes and one .dsc from this run, found {len(changes)} and {len(dscs)}", file=sys.stderr)
        return 2
    def checksums(path):
        """(name, sha256) pairs of a .changes or .dsc Checksums-Sha256 field."""
        pairs, section = [], None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line[0].isspace():
                section = line.split(":", 1)[0]
            elif section == "Checksums-Sha256" and line.strip():
                digest, _size, name = line.split()
                pairs.append((name, digest))
        return pairs
    listed = checksums(changes[0])
    if not listed:
        print(f"{changes[0].name} lists no files", file=sys.stderr)
        return 2
    # The source package: the .dsc and every file it names (orig/debian tarballs,
    # native tarball, diff.gz), taken with the hashes the .dsc records.
    source_files = checksums(dscs[0])
    source_names = {dscs[0].name} | {name for name, _ in source_files}
    selected = [(dscs[0], None, "source"), (changes[0], None, None)]
    for name, digest in source_files:
        path = dscs[0].parent / name
        if not path.is_file() or sha256(path) != digest:
            print(f"{name} listed in {dscs[0].name} is missing or does not match its sha256", file=sys.stderr)
            return 2
        selected.append((path, digest, "source_file"))
    try:
        leaked = vcs_entries(dscs[0].parent, [name for name, _ in source_files])
    except (OSError, EOFError, tarfile.TarError) as exc:
        print(f"cannot inspect the source files of {dscs[0].name} for VCS metadata: {exc}", file=sys.stderr)
        return 2
    if leaked:
        print("the source package contains version-control metadata; no manifest written:", file=sys.stderr)
        for entry in leaked:
            print(f"  {entry}", file=sys.stderr)
        return 2
    for name, digest in listed:
        path = changes[0].parent / name
        if not path.is_file() or sha256(path) != digest:
            print(f"{name} listed in {changes[0].name} is missing or does not match its sha256", file=sys.stderr)
            return 2
        if name in source_names:
            continue  # a source-full .changes: already recorded from the .dsc
        selected.append((path, digest, None))
    artifacts = []
    for path, _digest, role in selected:
        copied = output / path.name
        if path.resolve() != copied.resolve():
            copied.write_bytes(path.read_bytes())
            path = copied
        item = {"file": path.name, "sha256": sha256(path), "size": path.stat().st_size}
        if path.suffix in {".deb", ".ddeb", ".udeb"}:
            item.update({"kind": "binary", "package": run(["dpkg-deb", "-f", str(path), "Package"]).stdout.strip(),
                         "version": run(["dpkg-deb", "-f", str(path), "Version"]).stdout.strip(),
                         "architecture": run(["dpkg-deb", "-f", str(path), "Architecture"]).stdout.strip()})
        elif role == "source":
            item.update({"kind": "source", "package": package, "version": version})
        elif role == "source_file":
            item.update({"kind": "source_file", "package": package, "version": version})
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
