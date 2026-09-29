#!/usr/bin/env python3
"""The tested build of a gated build (UNITY-20260929-020).

ENGINEERING-PROCESS section 6: what the target test installed must be the
gated build, or equivalent to it. The release record names what the target
test installed and how that is tied to the gated build:

  "target_test": {"record": <repo path>, "debs": {<file name>: <sha256>, ...}},
  "tested_build": "this_build" | "same_chroot" | "buildinfo_identical",
  "tested_manifest": <repo path>      (same_chroot; optional for buildinfo_identical)
  "tested_buildinfo": <repo path>     (buildinfo_identical)
  "tested_changes": <repo path>       (buildinfo_identical without tested_manifest)

check() verifies it against the gated build manifest and the committed files
and returns the object the gate records as "tested_build" (every file with its
sha256). create_release_gate.py calls it with the release record;
publish_aptly.py calls it with fields_from_gate() of the gate's object and
refuses unless it recomputes the same object.
"""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_dependencies import installed_build_depends  # noqa: E402

MODES = ("this_build", "same_chroot", "buildinfo_identical")
SHA_RE = re.compile(r"[0-9a-f]{64}")
PATH_KEYS = ("tested_manifest", "tested_buildinfo", "tested_changes")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checksum_pairs(text):
    """[(name, sha256)] of a Checksums-Sha256 field (.changes, .dsc); raises
    ValueError on a malformed line or a file name listed twice."""
    pairs, section = [], None
    for line in text.splitlines():
        if line and not line[0].isspace():
            section = line.split(":", 1)[0]
        elif section == "Checksums-Sha256" and line.strip():
            parts = line.split()
            if len(parts) != 3 or not SHA_RE.fullmatch(parts[0]):
                raise ValueError(f"malformed Checksums-Sha256 line: {line.strip()!r}")
            pairs.append((parts[2], parts[0]))
    names = [name for name, _ in pairs]
    if len(names) != len(set(names)):
        raise ValueError("a file name is listed twice in Checksums-Sha256")
    return pairs


def buildinfo_fields(text):
    fields = {}
    for line in text.splitlines():
        if line and not line[0].isspace() and ":" in line:
            key, value = line.split(":", 1)
            fields[key] = value.strip()
    return fields


def committed(root, rel, label):
    """(path, sha256, error): rel is a repository-relative path of a tracked,
    committed, unmodified regular file."""
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None, None, f"{label} must be a repository-relative path"
    root = Path(root).resolve()
    path = (root / rel).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None, None, f"{label} {rel!r} is outside the repository"
    if not path.is_file():
        return None, None, f"{label} {rel!r} does not exist"
    run = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True)
    relpath = str(path.relative_to(root))
    if run("ls-files", "--error-unmatch", "--", relpath).returncode or run("status", "--porcelain", "--", relpath).stdout.strip():
        return None, None, f"{label} {rel!r} must be tracked, committed and unmodified"
    return path, sha256(path), None


def artifact_pairs(manifest, kind):
    return {(a.get("file"), a.get("sha256")) for a in manifest.get("artifacts") or []
            if isinstance(a, dict) and a.get("kind") == kind}


def dependency_identity(manifest):
    return sorted((e.get("package"), e.get("version"), e.get("architecture"), e.get("sha256"))
                  for e in manifest.get("build_dependencies") or [])


def check(fields, manifest, manifest_dir, root):
    """(tested_build object, error)."""
    chroot = manifest.get("chroot")
    if not isinstance(chroot, dict) or not isinstance(chroot.get("sha256"), str):
        return None, ("the gated build manifest has no chroot record: rebuild with scripts/build_sbuild.py "
                      "(UNITY-20260929-016)")
    mode = fields.get("tested_build")
    if mode not in MODES:
        return None, f"tested_build must be one of {', '.join(MODES)}, not {mode!r}"
    target = fields.get("target_test")
    if not isinstance(target, dict) or not isinstance(target.get("debs"), dict) or not target["debs"]:
        return None, "target_test must name the record and the debs the target test installed"
    debs = target["debs"]
    for name, digest in debs.items():
        if not isinstance(name, str) or not name.endswith(".deb") or "/" in name or not isinstance(digest, str) \
                or not SHA_RE.fullmatch(digest):
            return None, f"target_test.debs entry {name!r}: {digest!r} is not a .deb file name with a sha256"
    record_path, record_sha, error = committed(root, target.get("record"), "target_test.record")
    if error:
        return None, error
    record_text = record_path.read_text(encoding="utf-8", errors="replace")
    for name, digest in debs.items():
        if name not in record_text and digest not in record_text:
            return None, f"the target test record {target['record']} does not name {name}"
    wanted = set(debs.items())
    result = {"mode": mode, "target_test": {"record": {"file": target["record"], "sha256": record_sha},
                                            "debs": dict(sorted(debs.items()))}}

    if mode == "this_build":
        missing = wanted - artifact_pairs(manifest, "binary")
        if missing:
            return None, f"the target test installed debs that are not binaries of this build: {sorted(missing)}"
        return result, None

    tested = None
    if mode == "same_chroot" or fields.get("tested_manifest") is not None:
        tested_path, tested_sha, error = committed(root, fields.get("tested_manifest"), "tested_manifest")
        if error:
            return None, error
        try:
            tested = json.loads(tested_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            return None, f"tested_manifest is not JSON: {exc}"
        if not isinstance(tested, dict):
            return None, "tested_manifest is not a build manifest"
        missing = wanted - artifact_pairs(tested, "binary")
        if missing:
            return None, f"the target test installed debs that are not binaries of the tested build: {sorted(missing)}"
        result["tested_manifest"] = {"file": fields["tested_manifest"], "sha256": tested_sha}

    if mode == "same_chroot":
        link = chroot.get("tested_with")
        if not isinstance(link, dict) or link.get("manifest_sha256") != tested_sha:
            return None, "the gated build was not built --tested-with this tested manifest (manifest_sha256 differs)"
        for label, a, b in (("chroot", (tested.get("chroot") or {}).get("sha256"), chroot["sha256"]),
                            ("source_commit", tested.get("source_commit"), manifest.get("source_commit")),
                            ("source_tree_hash", tested.get("source_tree_hash"), manifest.get("source_tree_hash")),
                            ("build_dependencies", dependency_identity(tested), dependency_identity(manifest))):
            if a != b:
                return None, f"the tested and gated builds differ in {label}"
        return result, None

    # buildinfo_identical
    tb_path, tb_sha, error = committed(root, fields.get("tested_buildinfo"), "tested_buildinfo")
    if error:
        return None, error
    tb_pair = (Path(fields["tested_buildinfo"]).name, tb_sha)
    if tested is not None:
        if tb_pair not in artifact_pairs(tested, "buildinfo"):
            return None, "tested_buildinfo is not the .buildinfo of the tested manifest"
    else:
        ch_path, ch_sha, error = committed(root, fields.get("tested_changes"), "tested_changes")
        if error:
            return None, error
        try:
            listed = set(checksum_pairs(ch_path.read_text(encoding="utf-8", errors="replace")))
        except ValueError as exc:
            return None, f"tested_changes: {exc}"
        missing = (wanted | {tb_pair}) - listed
        if missing:
            return None, f"the tested .changes does not list {sorted(missing)}"
        result["tested_changes"] = {"file": fields["tested_changes"], "sha256": ch_sha}
    gated = [a for a in manifest.get("artifacts") or [] if isinstance(a, dict) and a.get("kind") == "buildinfo"]
    if len(gated) != 1:
        return None, f"the gated build manifest lists {len(gated)} .buildinfo files, not one"
    gb_path = Path(manifest_dir) / gated[0]["file"]
    if not gb_path.is_file() or sha256(gb_path) != gated[0].get("sha256"):
        return None, "the gated build's .buildinfo is missing or does not match its sha256"
    tested_text = tb_path.read_text(encoding="utf-8", errors="replace")
    gated_text = gb_path.read_text(encoding="utf-8", errors="replace")
    tf, gf = buildinfo_fields(tested_text), buildinfo_fields(gated_text)
    for key in ("Source", "Version", "Build-Architecture"):
        if tf.get(key) != gf.get(key):
            return None, f"the tested and gated .buildinfo differ in {key}: {tf.get(key)!r} / {gf.get(key)!r}"
    try:
        if installed_build_depends(tested_text) != installed_build_depends(gated_text):
            return None, "the tested and gated builds differ in Installed-Build-Depends; repeat the target test"
    except ValueError as exc:
        return None, f"cannot compare Installed-Build-Depends: {exc}"
    result["tested_buildinfo"] = {"file": fields["tested_buildinfo"], "sha256": tb_sha}
    result["gated_buildinfo"] = {"file": gated[0]["file"], "sha256": gated[0]["sha256"]}
    return result, None


def fields_from_gate(recorded):
    """The record fields a gate's tested_build object stands for."""
    if not isinstance(recorded, dict):
        return {}
    target = recorded.get("target_test") or {}
    fields = {"tested_build": recorded.get("mode"),
              "target_test": {"record": (target.get("record") or {}).get("file"), "debs": target.get("debs")}}
    for key in PATH_KEYS:
        if isinstance(recorded.get(key), dict):
            fields[key] = recorded[key].get("file")
    return fields


def publish_error(recorded, manifest, manifest_dir, root):
    """What publish_aptly.py calls: None when the gate's tested_build is
    recomputed exactly from the committed files, else an error."""
    if not isinstance(recorded, dict):
        return "the release gate has no tested_build record (UNITY-20260929-020)"
    result, error = check(fields_from_gate(recorded), manifest, manifest_dir, root)
    if error:
        return error
    if result != recorded:
        return "the gate's tested_build record does not match the committed files any more"
    return None
