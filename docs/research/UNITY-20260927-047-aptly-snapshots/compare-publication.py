#!/usr/bin/env python3
"""UNITY-20260927-047 phase R: compare two published trees (dists/<dist> of a
public root) file by file and field by field. Read-only.
Usage: compare-publication.py LABEL PUBLIC_A PUBLIC_B [DIST]
Prints: files only on one side, files with different bytes (Release,
InRelease and Release.gpg are compared by field and by signing key instead),
Release field differences, and the signing key of each InRelease."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys

SIGNED = {"Release", "InRelease", "Release.gpg"}


def files(root):
    return {str(p.relative_to(root)): p for p in root.rglob("*") if p.is_file()}


def release_fields(path):
    fields, key = {}, None
    for line in path.read_text().splitlines():
        if line and not line[0].isspace() and ":" in line:
            key, value = line.split(":", 1)
            fields[key] = value.strip()
        elif key:
            fields[key] += "\n" + line
    return fields


def signer(path):
    result = subprocess.run(["gpg", "--batch", "--status-fd", "1", "--verify", str(path)],
                            capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith("[GNUPG:] VALIDSIG"):
            return line.split()[2]
    return "NO VALID SIGNATURE"


def main():
    label, a, b = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    dist = sys.argv[4] if len(sys.argv) > 4 else "resolute"
    fa, fb = files(a / "dists" / dist), files(b / "dists" / dist)
    print(f"== {label}: {a}/dists/{dist} vs {b}/dists/{dist}")
    print("only in A:", sorted(set(fa) - set(fb)) or "none")
    print("only in B:", sorted(set(fb) - set(fa)) or "none")
    differ = [n for n in sorted(set(fa) & set(fb)) if Path(n).name not in SIGNED
              and hashlib.sha256(fa[n].read_bytes()).digest() != hashlib.sha256(fb[n].read_bytes()).digest()]
    print("index files with different bytes:", differ or "none")
    ra, rb = release_fields(fa["Release"]), release_fields(fb["Release"])
    diff = {k: (ra.get(k), rb.get(k)) for k in sorted(set(ra) | set(rb)) if ra.get(k) != rb.get(k)}
    print("Release fields that differ:", {k: (v[0][:60] if v[0] else v[0], v[1][:60] if v[1] else v[1]) for k, v in diff.items()} or "none")
    print("InRelease signed by: A", signer(fa["InRelease"]), "| B", signer(fb["InRelease"]))
    pa, pb = a / "pool", b / "pool"
    if pa.exists() and pb.exists():
        la = {str(p.relative_to(pa)) for p in pa.rglob("*") if p.is_file()}
        lb = {str(p.relative_to(pb)) for p in pb.rglob("*") if p.is_file()}
        print("public pool files: A", len(la), "B", len(lb), "same names:", la == lb)


if __name__ == "__main__":
    main()
