#!/usr/bin/env python3
"""Extra build dependencies of a build manifest (UNITY-20260929-013).

build_sbuild.py --extra-package records every package it gives sbuild beyond
the target series' archive in the manifest's optional `build_dependencies`
list; create_release_gate.py and publish_aptly.py check that list with
check_entries(). A manifest without the key is not affected.

"Our published pool" is POOL_ROOT only: the files of our published
repository, read as files. The unpublished staging directory next to it does
not count. Callers (tests) may pass another root.
"""

import hashlib
from pathlib import Path
import re

POOL_ROOT = Path("/srv/aptly/public/pool")

REQUIRED_FIELDS = ("file", "sha256", "size", "package", "version", "architecture", "source")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_name(source_field, package):
    """The source package name of a binary: its Source field without a
    '(version)' part, or the package name when the field is absent."""
    if source_field and source_field.strip():
        return source_field.split("(", 1)[0].strip()
    return package


def pool_path(root, package, version, architecture, source):
    """Where Debian's pool layout puts this .deb: pool/main/<prefix>/<source>/
    with prefix = 'libX' for lib* sources, else the first letter, and the
    canonical file name package_version-without-epoch_arch.deb."""
    prefix = source[:4] if source.startswith("lib") and len(source) > 3 else source[:1]
    name = f"{package}_{version.split(':', 1)[-1]}_{architecture}.deb"
    return Path(root) / "main" / prefix / source / name


def in_pool(root, package, version, architecture, source, digest):
    """(True, path) when the pool holds this package with exactly these bytes."""
    path = pool_path(root, package, version, architecture, source)
    try:
        return path.is_file() and sha256(path) == digest, path
    except OSError:
        return False, path


def installed_build_depends(text):
    """{(name, arch-qualifier or None): version} from a .buildinfo's
    Installed-Build-Depends field (multi-line, comma-separated entries of the
    form 'name[:arch] (= version)'). Raises ValueError when the field is
    missing or an entry does not have that form."""
    entries, inside = [], False
    for line in text.splitlines():
        if line.startswith("Installed-Build-Depends:"):
            inside = True
            entries.append(line.split(":", 1)[1])
        elif inside and line[:1].isspace():
            entries.append(line)
        elif inside:
            break
    if not inside:
        raise ValueError("the .buildinfo has no Installed-Build-Depends field")
    result = {}
    for part in ",".join(entries).split(","):
        part = part.strip()
        if not part:
            continue
        match = re.fullmatch(r"([a-z0-9][a-z0-9+.-]*)(?::([a-z0-9-]+))?\s*\(=\s*([^)\s]+)\s*\)", part)
        if not match:
            raise ValueError(f"unexpected Installed-Build-Depends entry: {part!r}")
        result[(match.group(1), match.group(2))] = match.group(3)
    return result


def manifest_error(manifest, manifest_dir, pool_root=None):
    """What create_release_gate.py and publish_aptly.py call: None for a
    manifest without build_dependencies (every manifest before
    UNITY-20260929-013, every build without --extra-package), else the result
    of check_entries()."""
    if "build_dependencies" not in manifest:
        return None
    return check_entries(manifest["build_dependencies"], manifest_dir, pool_root)


def check_entries(entries, manifest_dir, pool_root=None):
    """Return an error message or None for a manifest's build_dependencies:
    a list of entries with the required fields; each file relative and inside
    the manifest's directory, present, with its recorded sha256; the same
    bytes in our published pool at the path the package's own fields give
    (a recorded pool_path must lie inside the pool root, but is not trusted)."""
    root = Path(pool_root) if pool_root is not None else POOL_ROOT
    base = Path(manifest_dir).resolve()
    if not isinstance(entries, list) or not entries:
        return "build_dependencies must be a non-empty list"
    for entry in entries:
        if not isinstance(entry, dict) or not all(isinstance(entry.get(k), (str, int)) and entry.get(k) != ""
                                                  for k in REQUIRED_FIELDS):
            return f"build dependency record lacks one of {', '.join(REQUIRED_FIELDS)}: {entry!r}"
        name = entry["file"]
        if not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts:
            return f"build dependency file must be a relative path inside the manifest's directory: {name!r}"
        path = (base / name).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            return f"build dependency file resolves outside the manifest's directory: {name!r}"
        if not path.is_file() or sha256(path) != entry["sha256"]:
            return f"build dependency {name} is missing or does not match its sha256"
        recorded = entry.get("pool_path")
        if recorded is not None:
            try:
                Path(recorded).resolve().relative_to(root.resolve())
            except ValueError:
                return f"build dependency {name}: recorded pool_path {recorded!r} is outside {root}"
        found, where = in_pool(root, entry["package"], entry["version"], entry["architecture"],
                               entry["source"], entry["sha256"])
        if not found:
            return f"build dependency {name} ({entry['package']} {entry['version']}) is not in our published pool with these bytes ({where})"
    return None
