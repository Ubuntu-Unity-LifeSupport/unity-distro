#!/usr/bin/env python3
"""UNITY-20260927-047 phase R preparation: build /var/tmp/aptly-rehearsal from
reads of /srv/aptly only. aptly is not run.

- The root and its directories are 0700, and aptly.conf is the live config
  with rootDir moved into the root (UNITY-20260927-057 schema keys only).
- incoming/ holds copies (new inodes, no links) of the repository's 285
  package records: the 258 binaries of the published Packages index, matched
  by file name and SHA256, and the 27 source packages (every .dsc in the
  pool plus the files its Checksums-Sha256 names). Every copy is checked
  against its sha256.
- A sha256 list of every file under /srv/aptly is taken before and after, to
  show that nothing there changed.

Usage: prepare-rehearsal.py OUTPUT_LOG
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

LIVE = Path("/srv/aptly")
ROOT = Path("/var/tmp/aptly-rehearsal")
PACKAGES = LIVE / "public/dists/resolute/main/binary-amd64/Packages"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def tree(path):
    return {str(p.relative_to(path)): sha256(p) for p in sorted(path.rglob("*")) if p.is_file() and not p.is_symlink()}


def stanzas(text):
    for block in text.split("\n\n"):
        fields = {}
        for line in block.splitlines():
            if line and not line[0].isspace() and ":" in line:
                key, value = line.split(":", 1)
                fields[key] = value.strip()
        if fields:
            yield fields


def main():
    log = []
    before = tree(LIVE)
    log.append(f"/srv/aptly files before: {len(before)}")
    if ROOT.exists():
        sys.exit(f"{ROOT} exists already; not touching it")
    os.umask(0o077)
    ROOT.mkdir(mode=0o700)
    incoming = ROOT / "incoming"
    incoming.mkdir(mode=0o700)

    pool = {}
    for path in (LIVE / "pool").rglob("*"):
        if path.is_file():
            pool.setdefault(path.name.split("_", 1)[1], []).append(path)

    def take(name, digest):
        matches = [p for p in pool.get(name, []) if sha256(p) == digest]
        if len(matches) != 1:
            sys.exit(f"{name}: {len(matches)} pool files with sha256 {digest}")
        target = incoming / name
        if target.exists():
            if sha256(target) != digest:
                sys.exit(f"{name}: two different files with the same name")
            return False
        shutil.copyfile(matches[0], target)
        os.chmod(target, 0o600)
        if sha256(target) != digest:
            sys.exit(f"{name}: copy does not match")
        return True

    binaries = 0
    for fields in stanzas(PACKAGES.read_text()):
        take(Path(fields["Filename"]).name, fields["SHA256"])
        binaries += 1
    sources = 0
    source_files = 0
    for dscs in [v for k, v in pool.items() if k.endswith(".dsc")]:
        for dsc in dscs:
            take(dsc.name.split("_", 1)[1], sha256(dsc))
            sources += 1
            block = dsc.read_text().split("Checksums-Sha256:\n", 1)[1]
            for line in block.splitlines():
                if not line.startswith(" "):
                    break
                digest, _, name = line.split()
                if take(name, digest):
                    source_files += 1
    log.append(f"binary packages (Packages index): {binaries}")
    log.append(f"source packages (.dsc in pool): {sources}; their other files copied: {source_files}")
    log.append(f"incoming files: {len(list(incoming.iterdir()))}")

    config = {"rootDir": str(ROOT / "state"), "downloadConcurrency": 4, "architectures": ["amd64"],
              "gpgDisableSign": False, "gpgDisableVerify": False, "FileSystemPublishEndpoints": {}}
    (ROOT / "aptly.conf").write_text(json.dumps(config, indent=2) + "\n")
    os.chmod(ROOT / "aptly.conf", 0o600)
    log.append("aptly.conf: " + json.dumps(config))

    after = tree(LIVE)
    log.append(f"/srv/aptly files after: {len(after)}; unchanged: {before == after}")
    if before != after:
        sys.exit("/srv/aptly changed during the preparation")
    manifest = {name: sha256(incoming / name) for name in sorted(os.listdir(incoming))}
    Path(sys.argv[1]).write_text("\n".join(log) + "\n\n## incoming sha256\n" +
                                 "".join(f"{v}  {k}\n" for k, v in manifest.items()))
    print("\n".join(log))


if __name__ == "__main__":
    main()
