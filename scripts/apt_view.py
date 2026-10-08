#!/usr/bin/env python3
"""Measure what a target system's apt sees, in an isolated apt state.

Full view (--snapshot and --manifest): the Ubuntu archive pockets of
docs/apt/target.sources plus our repository as the gated aptly snapshot will
publish it, modelled as a local repository; reports apt's candidate for every
binary of the build manifest and the source versions per archive pocket.

Pocket view (--source-package only): the source versions per archive pocket,
for the ordering check before a build exists.

The host's apt configuration is neither read nor changed. Output is JSON; it
is evidence for scripts/version_safety.py, never hand-written.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile

TOOL = "apt_view.py"
TOOL_VERSION = 1
ROOT = Path(__file__).resolve().parents[1]
POCKETS = ("resolute", "resolute-updates", "resolute-security", "resolute-backports", "resolute-proposed")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def run(args, env=None, check=True):
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(f"{' '.join(args)} failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}")
    return result


def aptly(config, *args):
    return run(["aptly"] + ([f"-config={config}"] if config else []) + list(args)).stdout


def snapshot_model(config, snapshot):
    """The snapshot's full package list (its identity) and its deb/ddeb entries."""
    shown = aptly(config, "snapshot", "show", "-with-packages", snapshot)
    listed = sorted(line.strip() for line in shown.split("Packages:", 1)[-1].splitlines() if line.strip())
    debs = sorted(line.strip() for line in aptly(config, "snapshot", "search", snapshot, "$PackageType (deb)").splitlines()
                  if line.strip())
    return listed, debs


# Every record: a bare "Name" also matches only a package called "name" when lowercased.
ALL_PACKAGES = "Name (% *)"


def snapshot_identity_lines(config, snapshot):
    """Sorted per-package identity lines of the snapshot (UNITY-20261008-005).
    Binaries: "<aptly key>|<sha256 of the file>". Sources: "<aptly key>|<the
    .dsc's Checksums-Sha256 entries, sorted>". Unlike the names, these change
    when a record is replaced by other bytes under the same name and version."""
    lines, source_keys = [], set()
    for line in aptly(config, "snapshot", "search", "-format", '{{.Key}}|{{index . "SHA256"}}',
                      snapshot, ALL_PACKAGES).splitlines():
        if not line.strip():
            continue
        key, _, digest = line.strip().rpartition("|")
        if key.startswith("Psource "):
            source_keys.add(key)
        elif not key or not digest:
            raise RuntimeError(f"snapshot {snapshot}: binary record {line.strip()!r} has no SHA256")
        else:
            lines.append(f"{key}|{digest}")
    if source_keys:  # a search without results exits 1, so only when there are sources
        blocks, key = {}, None
        for line in aptly(config, "snapshot", "search", "-format", '{{.Key}}{{"\\n"}}{{index . "Checksums-Sha256"}}',
                          snapshot, "$Architecture (source)").splitlines():
            if line and not line[0].isspace():
                key = line.strip()
                blocks.setdefault(key, [])
            elif line.strip() and key is not None:
                blocks[key].append(" ".join(line.split()))
        if set(blocks) != source_keys:
            raise RuntimeError(f"snapshot {snapshot}: the source records differ between the two searches "
                               f"({sorted(source_keys ^ set(blocks))})")
        for key, entries in sorted(blocks.items()):
            if not entries:
                raise RuntimeError(f"snapshot {snapshot}: source record {key!r} has no Checksums-Sha256")
            lines.append(f"{key}|{','.join(sorted(entries))}")
    return sorted(lines)


def write_model_repo(directory, debs, release, marker):
    stanzas = []
    for entry in debs:
        name, rest = entry.split("_", 1)
        version, arch = rest.rsplit("_", 1)
        stanzas.append(f"Package: {name}\nVersion: {version}\nArchitecture: {arch}\n")
    (directory / "Packages").write_text("\n".join(stanzas), encoding="utf-8")
    options = []
    for key in ("Origin", "Label", "Suite", "Codename"):
        options += ["-o", f"APT::FTPArchive::Release::{key}={release[key]}"]
    # apt names list files after the URI with its own quoting ("_" -> "%5f", ...),
    # so the model Release is recognised by this per-run marker, not by file name.
    options += ["-o", f"APT::FTPArchive::Release::Description={marker}"]
    release_text = run(["apt-ftparchive"] + options + ["release", str(directory)]).stdout
    (directory / "Release").write_text(release_text, encoding="utf-8")


def release_fields(path):
    fields = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line[0].isspace() or ":" not in line:
            if line.startswith("-----BEGIN PGP SIGNATURE"):
                break
            continue
        key, _, value = line.partition(":")
        if key in ("Origin", "Label", "Suite", "Codename", "Date", "Valid-Until", "Description"):
            fields[key] = value.strip()
    return fields


def pocket_versions(env, source):
    """Highest version of the source package per pocket, from Sources indices."""
    showsrc = run(["apt-cache", "showsrc", "--only-source", source], env=env, check=False).stdout
    known = set()
    current = None
    for line in showsrc.splitlines():
        if line.startswith("Package:"):
            current = line.split(":", 1)[1].strip()
        elif line.startswith("Version:") and current == source:
            known.add(line.split(":", 1)[1].strip())
    per_pocket = {}
    madison = run(["apt-cache", "madison", source], env=env, check=False).stdout
    for line in madison.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3 or parts[0] != source or not parts[2].endswith(" Sources"):
            continue
        version, where = parts[1], parts[2][: -len(" Sources")].split()
        if version not in known or len(where) < 2:
            continue
        pocket = where[1].split("/", 1)[0]
        per_pocket.setdefault(pocket, []).append(version)
    result = {}
    for pocket, versions in per_pocket.items():
        best = versions[0]
        for version in versions[1:]:
            if run(["dpkg", "--compare-versions", version, "gt", best], check=False).returncode == 0:
                best = version
        result[pocket] = best
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-package", help="source package name (pocket view, or checked against the manifest)")
    parser.add_argument("--manifest", type=Path, help="build_sbuild.py manifest (full view)")
    parser.add_argument("--snapshot", help="gated aptly snapshot name (full view)")
    parser.add_argument("--aptly-config", help="aptly -config file (default: aptly's own)")
    parser.add_argument("--sources", type=Path, default=ROOT / "docs/apt/target.sources")
    parser.add_argument("--preferences-dir", type=Path, default=ROOT / "docs/apt/preferences.d")
    parser.add_argument("--release", default=". resolute|. resolute|resolute|resolute",
                        help="Origin|Label|Suite|Codename of our publication for the model repository")
    parser.add_argument("--write", type=Path, help="write the JSON here (default: stdout)")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("refusing to run as root")
    full = bool(args.snapshot or args.manifest)
    if full and not (args.snapshot and args.manifest):
        parser.error("a full view needs both --snapshot and --manifest")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if full else None
    source = manifest["package"] if manifest else args.source_package
    if not source or (manifest and args.source_package and args.source_package != source):
        parser.error("--source-package missing or different from the manifest's package")
    release = dict(zip(("Origin", "Label", "Suite", "Codename"), args.release.split("|")))
    if len(release) != 4:
        parser.error("--release needs Origin|Label|Suite|Codename")

    view = {"schema": 1, "tool": TOOL, "tool_version": TOOL_VERSION, "mode": "full" if full else "pockets",
            "source_package": source,
            "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "sources_file": str(args.sources), "sources_sha256": sha256_file(args.sources),
            "preferences": {p.name: sha256_file(p) for p in sorted(args.preferences_dir.glob("*")) if p.is_file()}}
    marker = f"apt_view model {secrets.token_hex(16)}"
    with tempfile.TemporaryDirectory(prefix="apt-view-") as tmp:
        t = Path(tmp)
        for sub in ("state/lists/partial", "cache/archives/partial", "sources.list.d", "preferences.d", "model"):
            (t / sub).mkdir(parents=True)
        (t / "sources.list.d" / "target.sources").write_text(args.sources.read_text(encoding="utf-8"), encoding="utf-8")
        for pref in args.preferences_dir.glob("*"):
            if pref.is_file():
                (t / "preferences.d" / pref.name).write_text(pref.read_text(encoding="utf-8"), encoding="utf-8")
        if full:
            listed, debs = snapshot_model(args.aptly_config, args.snapshot)
            content = snapshot_identity_lines(args.aptly_config, args.snapshot)
            view["snapshot"] = {"name": args.snapshot, "packages": len(listed),
                                "list_sha256": sha256_bytes(("\n".join(listed) + "\n").encode()),
                                "content_sha256": sha256_bytes(("\n".join(content) + "\n").encode()),
                                "model_entries": len(debs)}
            write_model_repo(t / "model", debs, release, marker)
            view["snapshot"]["model_release"] = release
            (t / "sources.list.d" / "model.sources").write_text(
                f"Types: deb\nURIs: file:{t / 'model'}/\nSuites: ./\nTrusted: yes\n", encoding="utf-8")
        conf = t / "apt.conf"
        conf.write_text("\n".join([
            f'Dir::State "{t}/state";', 'Dir::State::status "/dev/null";', f'Dir::Cache "{t}/cache";',
            'Dir::Etc::SourceList "/dev/null";', f'Dir::Etc::SourceParts "{t}/sources.list.d";',
            'Dir::Etc::Preferences "/dev/null";', f'Dir::Etc::PreferencesParts "{t}/preferences.d";',
            'APT::Architecture "amd64";', 'APT::Architectures { "amd64"; };', 'Acquire::Languages "none";',
            'APT::Sandbox::User "";', 'APT::Update::Error-Mode "any";', ""]), encoding="utf-8")
        env = dict(os.environ, APT_CONFIG=str(conf), LC_ALL="C")
        update = run(["apt-get", "update"], env=env, check=False)
        if update.returncode or re.search(r"(?m)^(E|W|Err):", update.stdout + update.stderr):
            print(f"apt-get update failed or warned; refusing:\n{update.stdout}{update.stderr}", file=sys.stderr)
            return 2
        view["releases"] = []
        for path in sorted((t / "state/lists").glob("*Release")):
            if path.name.endswith("_Release") and (t / "state/lists" / path.name.replace("_Release", "_InRelease")).exists():
                continue
            fields = release_fields(path)
            model = full and fields.pop("Description", None) == marker
            fields.pop("Description", None)
            entry = {"file": "<model>_Release" if model else path.name, "sha256": sha256_file(path), "model": model}
            entry.update(fields)
            view["releases"].append(entry)
        view["pockets"] = pocket_versions(env, source)
        view["in_archive"] = bool(set(view["pockets"]) & set(POCKETS))
        if full:
            view["binaries"] = []
            for artifact in manifest["artifacts"]:
                if artifact.get("kind") != "binary" or artifact["file"].endswith(".udeb"):
                    continue
                policy = run(["apt-cache", "policy", artifact["package"]], env=env).stdout
                match = re.search(r"(?m)^\s*Candidate:\s*(\S+)\s*$", policy)
                view["binaries"].append({"package": artifact["package"], "version": artifact["version"],
                                         "architecture": artifact["architecture"], "file": artifact["file"],
                                         "apt_candidate": match.group(1) if match else None,
                                         "policy": policy.replace(str(t), "<VIEW>")})
    output = json.dumps(view, indent=2) + "\n"
    if args.write:
        args.write.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
