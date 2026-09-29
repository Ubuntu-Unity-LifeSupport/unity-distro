#!/usr/bin/env python3
"""Decide version safety from a measured apt view (scripts/apt_view.py).

Full check:      version_safety.py --view VIEW.json --manifest MANIFEST.json
Pre-build check: version_safety.py --view POCKETS.json --pre-build
                                   --candidate-version V --source-commit C

The view must come from apt_view.py; typed records are not accepted. A full
check is SAFE only if the candidate source version is newer than the highest
version of that source in each measured archive pocket and a target system's
apt, with our repository as the gated snapshot, selects every binary of the
build at that binary's own version (a binNMU included). The pre-build check
judges the ordering only and is never SAFE.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

# Pocket -> verdict when the candidate is not newer than that pocket's version.
POCKET_RULES = {
    "resolute-security": "REPLACES_SECURITY_UPDATE",
    "resolute-updates": "REPLACES_SECURITY_UPDATE",
    "resolute-proposed": "BLOCKS_FUTURE_UPDATE",
    "resolute": "UNSAFE",
    "resolute-backports": "UNSAFE",
}
TARGET_SERIES = "resolute"


def newer(left, right):
    return subprocess.run(["dpkg", "--compare-versions", left, "gt", right], check=False).returncode == 0


def ordering(candidate, pockets):
    """Return (verdict or None, reasons) for the source-version ordering."""
    unknown = sorted(set(pockets) - set(POCKET_RULES))
    if unknown:
        return "UNKNOWN", [f"view has pockets without a rule: {', '.join(unknown)}"]
    for pocket, verdict in POCKET_RULES.items():
        if pocket in pockets and not newer(candidate, pockets[pocket]):
            return verdict, [f"candidate {candidate} is not newer than {pockets[pocket]} in {pocket}"]
    if not pockets:
        return None, ["source is not in any archive pocket (not in archive)"]
    return None, [f"candidate {candidate} is newer than " + ", ".join(f"{p} {v}" for p, v in sorted(pockets.items()))]


def decide(view, manifest=None, pre_build=False, candidate=None, source_commit=None):
    result = {"schema": 2, "result": "UNKNOWN", "reasons": [], "target_series": TARGET_SERIES}
    if not isinstance(view, dict) or view.get("tool") != "apt_view.py" or view.get("schema") != 1:
        result["reasons"].append("the view is not apt_view.py output; typed records are not accepted")
        return result
    expected_mode = "pockets" if pre_build else "full"
    if view.get("mode") != expected_mode:
        result["reasons"].append(f"a {'pre-build' if pre_build else 'full'} check needs a {expected_mode} view")
        return result
    if pre_build:
        source, candidate_version = view.get("source_package"), candidate
    else:
        if not isinstance(manifest, dict):
            result["reasons"].append("a full check needs the build manifest")
            return result
        source, candidate_version, source_commit = manifest.get("package"), manifest.get("candidate_version"), manifest.get("source_commit")
        if view.get("source_package") != source:
            result["reasons"].append("view and manifest name different source packages")
            return result
    if not source or not candidate_version or not source_commit:
        result["reasons"].append("source package, candidate version and source commit are required")
        return result
    pockets = view.get("pockets")
    if not isinstance(pockets, dict):
        result["reasons"].append("view has no pocket versions")
        return result
    result.update(source_package=source, source_commit=source_commit, candidate_source_version=candidate_version,
                  pockets=pockets, in_archive=view.get("in_archive"), checked_at=view.get("measured_at"),
                  mode=view.get("mode"))
    verdict, reasons = ordering(candidate_version, pockets)
    result["reasons"] += reasons
    if verdict:
        result["result"] = verdict
        return result
    if pre_build:
        result["reasons"].append("pre-build check: ordering only; apt selection not measured, never SAFE")
        return result
    built = sorted((a["package"], a["version"], a["architecture"]) for a in manifest.get("artifacts", [])
                   if a.get("kind") == "binary" and not a.get("file", "").endswith(".udeb"))
    measured = view.get("binaries") or []
    if sorted((b.get("package"), b.get("version"), b.get("architecture")) for b in measured) != built or not built:
        result["reasons"].append("the view's binaries are not the manifest's binaries")
        return result
    result["binaries"] = [{"package": b["package"], "version": b["version"], "architecture": b["architecture"],
                           "apt_candidate": b.get("apt_candidate")} for b in measured]
    result["snapshot"] = view.get("snapshot")
    wrong = [f"{b['package']}: apt selects {b.get('apt_candidate')}, built {b['version']}" for b in measured
             if b.get("apt_candidate") != b["version"]]
    if wrong:
        result["result"] = "UNSAFE"
        result["reasons"] += wrong
        return result
    result["result"] = "SAFE"
    result["reasons"].append("every built binary is apt's candidate at its own version in the target view")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--view", type=Path, required=True, help="apt_view.py output")
    parser.add_argument("--manifest", type=Path, help="build_sbuild.py manifest (full check)")
    parser.add_argument("--pre-build", action="store_true", help="ordering-only check before a build exists")
    parser.add_argument("--candidate-version", help="pre-build: the planned source version")
    parser.add_argument("--source-commit", help="pre-build: the source commit")
    parser.add_argument("--write", type=Path, help="write result JSON here; defaults to stdout")
    args = parser.parse_args()
    try:
        raw = args.view.read_bytes()
        view = json.loads(raw)
        manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else None
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"cannot read input: {exc}")
    result = decide(view, manifest, args.pre_build, args.candidate_version, args.source_commit)
    result["view_sha256"] = hashlib.sha256(raw).hexdigest()
    output = json.dumps(result, indent=2) + "\n"
    if args.write:
        args.write.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0 if result["result"] == "SAFE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
