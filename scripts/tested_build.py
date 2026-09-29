#!/usr/bin/env python3
"""The tested build of a gated build (UNITY-20260929-020).

ENGINEERING-PROCESS section 6: what the target test installed must be the
gated build, or equivalent to it. The release record names what the target
test installed and how that is tied to the gated build:

  "target_test": {"record": <repo path>, "debs": {<file name>: <sha256>, ...}},
  "tested_build": "this_build" | "same_chroot" | "buildinfo_identical",
  "tested_manifest": <repo path>      (same_chroot, buildinfo_identical)
  "tested_buildinfo": <repo path>     (buildinfo_identical)

The tested build is always identified by a committed build_sbuild manifest
(source commit and tree, artifact hashes): no other tool output ties a
binary build to its source (Verifier round 1, design review 4). A tested
build made without one needs a new target test.

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
PATH_KEYS = ("tested_manifest", "tested_buildinfo")
BUILDINFO_FIELDS = ("Source", "Binary", "Architecture", "Version", "Build-Architecture")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def buildinfo_fields(text):
    fields = {}
    for line in text.splitlines():
        if line and not line[0].isspace() and ":" in line:
            key, value = line.split(":", 1)
            fields[key] = value.strip()
    return fields


def committed(root, rel, label):
    """(path, normalized relative path, sha256, error): rel is a
    repository-relative path, without '..' and without symlinks on the way, of
    a tracked, committed, unmodified regular file."""
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        return None, None, None, f"{label} must be a repository-relative path without '..'"
    root = Path(root).resolve()
    walked = root
    for part in Path(rel).parts:
        walked = walked / part
        if walked.is_symlink():
            return None, None, None, f"{label} {rel!r} passes through a symlink"
    path = walked
    if not path.is_file():
        return None, None, None, f"{label} {rel!r} does not exist"
    run = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True)
    relpath = path.relative_to(root).as_posix()
    if run("ls-files", "--error-unmatch", "--", relpath).returncode or run("status", "--porcelain", "--", relpath).stdout.strip():
        return None, None, None, f"{label} {rel!r} must be tracked, committed and unmodified"
    return path, relpath, sha256(path), None


def artifact_pairs(manifest, kind):
    return {(a.get("file"), a.get("sha256")) for a in manifest.get("artifacts") or []
            if isinstance(a, dict) and a.get("kind") == kind}


def dependency_identity(manifest):
    return sorted(tuple(str(e.get(k)) for k in ("package", "version", "architecture", "sha256"))
                  for e in manifest.get("build_dependencies") or [] if isinstance(e, dict))


def names_file(text, name):
    """The record names this exact file name as a whole word (a path before it,
    as in ./name or dir/name, is fine; xname or name.bak is not)."""
    return re.search(r"(?<![A-Za-z0-9._+~:-])" + re.escape(name) + r"(?![A-Za-z0-9._+~:-])", text) is not None


def duplicate_ibd(text):
    """A package listed twice in Installed-Build-Depends (the parser keeps the last)."""
    entries, inside = [], False
    for line in text.splitlines():
        if line.startswith("Installed-Build-Depends:"):
            inside = True
            entries.append(line.split(":", 1)[1])
        elif inside and line[:1].isspace():
            entries.append(line)
        elif inside:
            break
    names = [part.strip().split(" ", 1)[0] for part in ",".join(entries).split(",") if part.strip()]
    return sorted({n for n in names if names.count(n) > 1})


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
    record_path, record_rel, record_sha, error = committed(root, target.get("record"), "target_test.record")
    if error:
        return None, error
    record_text = record_path.read_text(encoding="utf-8", errors="replace")
    for name in debs:
        if not names_file(record_text, name):
            return None, f"the target test record {record_rel} does not name {name}"
    wanted = set(debs.items())
    result = {"mode": mode, "target_test": {"record": {"file": record_rel, "sha256": record_sha},
                                            "debs": dict(sorted(debs.items()))}}

    if mode == "this_build":
        missing = wanted - artifact_pairs(manifest, "binary")
        if missing:
            return None, f"the target test installed debs that are not binaries of this build: {sorted(missing)}"
        return result, None

    # same_chroot and buildinfo_identical: the tested build's committed
    # build_sbuild manifest identifies it (source commit and tree, artifacts).
    tested_path, tested_rel, tested_sha, error = committed(root, fields.get("tested_manifest"), "tested_manifest")
    if error:
        return None, error
    try:
        tested = json.loads(tested_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return None, f"tested_manifest is not JSON: {exc}"
    if not isinstance(tested, dict) or tested.get("schema") != 1 or not tested.get("source_commit") \
            or not tested.get("source_tree_hash"):
        return None, "tested_manifest is not a build_sbuild manifest with its source commit and tree"
    missing = wanted - artifact_pairs(tested, "binary")
    if missing:
        return None, f"the target test installed debs that are not binaries of the tested build: {sorted(missing)}"
    result["tested_manifest"] = {"file": tested_rel, "sha256": tested_sha}
    for label, a, b in (("source_commit", tested.get("source_commit"), manifest.get("source_commit")),
                        ("source_tree_hash", tested.get("source_tree_hash"), manifest.get("source_tree_hash")),
                        ("build_dependencies", dependency_identity(tested), dependency_identity(manifest))):
        if a != b:
            return None, f"the tested and gated builds differ in {label}"

    if mode == "same_chroot":
        link = chroot.get("tested_with")
        if not isinstance(link, dict) or link.get("manifest_sha256") != tested_sha:
            return None, "the gated build was not built --tested-with this tested manifest (manifest_sha256 differs)"
        if (tested.get("chroot") or {}).get("sha256") != chroot["sha256"]:
            return None, "the tested and gated builds differ in chroot"
        return result, None

    # buildinfo_identical
    tb_path, tb_rel, tb_sha, error = committed(root, fields.get("tested_buildinfo"), "tested_buildinfo")
    if error:
        return None, error
    if (tb_path.name, tb_sha) not in artifact_pairs(tested, "buildinfo"):
        return None, "tested_buildinfo is not the .buildinfo of the tested manifest"
    gated = [a for a in manifest.get("artifacts") or [] if isinstance(a, dict) and a.get("kind") == "buildinfo"]
    if len(gated) != 1:
        return None, f"the gated build manifest lists {len(gated)} .buildinfo files, not one"
    gb_path = Path(manifest_dir) / gated[0]["file"]
    if not gb_path.is_file() or sha256(gb_path) != gated[0].get("sha256"):
        return None, "the gated build's .buildinfo is missing or does not match its sha256"
    tested_text = tb_path.read_text(encoding="utf-8", errors="replace")
    gated_text = gb_path.read_text(encoding="utf-8", errors="replace")
    tf, gf = buildinfo_fields(tested_text), buildinfo_fields(gated_text)
    for key in BUILDINFO_FIELDS:
        if tf.get(key) != gf.get(key):
            return None, f"the tested and gated .buildinfo differ in {key}: {tf.get(key)!r} / {gf.get(key)!r}"
    for label, text in (("tested", tested_text), ("gated", gated_text)):
        twice = duplicate_ibd(text)
        if twice:
            return None, f"the {label} .buildinfo lists {', '.join(twice)} twice in Installed-Build-Depends"
    try:
        if installed_build_depends(tested_text) != installed_build_depends(gated_text):
            return None, "the tested and gated builds differ in Installed-Build-Depends; repeat the target test"
    except ValueError as exc:
        return None, f"cannot compare Installed-Build-Depends: {exc}"
    result["tested_buildinfo"] = {"file": tb_rel, "sha256": tb_sha}
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
