#!/usr/bin/env python3
"""Build release-gate.json from a validated review record and build manifest."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_dependencies import manifest_error  # noqa: E402


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, type=Path, help="review/version/peer evidence JSON")
    parser.add_argument("--build-manifest", required=True, type=Path)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--prefix", default=".")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    record_path = args.record.resolve(); manifest_path = args.build_manifest.resolve()
    for path in (record_path, manifest_path, args.output.resolve()):
        try: path.relative_to(root)
        except ValueError: parser.error("records and output must be inside the repository")
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"cannot read input JSON: {exc}")
    if not isinstance(record, dict) or not isinstance(manifest, dict): parser.error("input JSON files must contain objects")
    match = re.fullmatch(r"UNITY-\d{8}-\d{3,}", str(record.get("task_id", "")))
    if not match: parser.error("record requires a valid task_id")
    fields = ("task_id", "package", "target_series", "candidate_version", "source_commit")
    for field in fields:
        if record.get(field) != manifest.get("task_id" if field == "task_id" else field):
            parser.error(f"build manifest and record do not match for {field}")
    if manifest.get("result") != "PASS" or manifest.get("schema") != 1:
        parser.error("build manifest is not a passing supported manifest")
    verification = record.get("verification_result")
    if verification == "NOT_APPLICABLE":
        if record.get("verification_scope") != "MECHANICAL_PACKAGING_ONLY" or not record.get("verification_reason"):
            parser.error("NOT_APPLICABLE requires a mechanical-only scope and reason")
    elif verification != "PASS": parser.error("verification_result must be PASS or documented NOT_APPLICABLE")
    if record.get("peer_notice") not in {"ACK", "COORDINATOR_CONFIRMED_NO_CONFLICT"}:
        parser.error("peer_notice must record an acknowledgement or coordinator confirmation")
    if not record.get("patch_and_decision_docs"):
        parser.error("patch_and_decision_docs evidence is required")
    if record.get("source_provenance") != "PUSHED":
        parser.error("only a source commit present in a remote-tracking ref can be published")
    repo = Path(manifest["source_repo"])
    if not repo.is_absolute(): repo = root / repo
    if not repo.is_dir(): parser.error("source_repo in manifest is unavailable")
    try:
        import subprocess
        actual = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        tree = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], check=True, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc: parser.error(f"cannot inspect source repository: {exc}")
    if dirty or actual != manifest.get("source_commit") or tree != manifest.get("source_tree_hash"):
        parser.error("source repository must be clean and match the build manifest commit and tree")
    try: repo.resolve().relative_to((root / "packages").resolve())
    except ValueError: parser.error("source repository must be a package checkout under packages/")
    if repo.name != record.get("package"): parser.error("source repository directory must match source package name")
    board = Path.home() / "coordinator/TASKS.md"
    if not board.is_file(): parser.error("private task board is unavailable")
    rows = [line for line in board.read_text(encoding="utf-8").splitlines() if len(line.strip("|").split("|")) > 1 and line.strip("|").split("|")[0].strip() == record["task_id"]]
    if len(rows) != 1 or rows[0].strip("|").split("|")[4].strip() not in {"REVIEW", "READY_TO_PUBLISH"}:
        parser.error("gate can be generated only while the task is in REVIEW or READY_TO_PUBLISH")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts: parser.error("manifest has no artifacts")
    for artifact in artifacts:
        path = args.build_manifest.parent / artifact.get("file", "")
        if not path.is_file() or digest(path) != artifact.get("sha256"):
            parser.error(f"missing or changed build artifact: {path}")
    # UNITY-20260929-013: extra build dependencies, only when the build had any.
    dependency_error = manifest_error(manifest, args.build_manifest.parent)
    if dependency_error: parser.error(dependency_error)
    if not args.snapshot or not args.distribution: parser.error("snapshot and distribution are required")
    evidence_paths = record.get("evidence", {})
    if not isinstance(evidence_paths, dict) or not all(isinstance(evidence_paths.get(key), str) for key in ("evidence_card", "verification_record", "patch_record")):
        parser.error("record evidence requires evidence_card and verification_record paths")
    evidence_paths["release_record"] = str(record_path.relative_to(root))
    evidence_paths["version_check"] = record.get("version_check")
    if not isinstance(evidence_paths["version_check"], str): parser.error("release record must include a version_check path")
    # version_check is the apt_view.py measurement of this snapshot; compute the verdict, do not trust a typed one.
    import subprocess as _sp
    view_path = (root / evidence_paths["version_check"]).resolve()
    verdict_run = _sp.run([sys.executable, str(root / "scripts/version_safety.py"), "--view", str(view_path),
                           "--manifest", str(args.build_manifest)], check=False, capture_output=True, text=True)
    try: verdict = json.loads(verdict_run.stdout)
    except json.JSONDecodeError: parser.error("version_safety.py did not return valid JSON")
    if verdict.get("result") != "SAFE": parser.error(f"version check is not SAFE: {verdict.get('reasons')}")
    if (verdict.get("snapshot") or {}).get("name") != args.snapshot:
        parser.error("the version check measured another snapshot than the gate names")
    if record.get("decision_required") is True and not isinstance(evidence_paths.get("decision_record"), str):
        parser.error("decision_record evidence is required when a material design decision was made")
    evidence_manifest = {"schema": 1, "task_id": record["task_id"], "package": record["package"],
                         "source_commit": manifest["source_commit"], "files": {}}
    for key, rel in evidence_paths.items():
        path = (root / rel).resolve()
        try: path.relative_to(root)
        except ValueError: parser.error(f"evidence {key} must be inside the repository")
        if not path.is_file(): parser.error(f"evidence file is missing: {path}")
        evidence_manifest["files"][key] = {"file": str(path.relative_to(root)), "sha256": digest(path)}
    gate_path = args.output.resolve()
    evidence_manifest_path = gate_path.with_name("evidence-manifest.json")
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_manifest_path.write_text(json.dumps(evidence_manifest, indent=2) + "\n", encoding="utf-8")
    gate = {
        "schema": 1, "task_id": record["task_id"], "package": record["package"],
        "target_series": record["target_series"], "candidate_version": record["candidate_version"],
        "task_state": "READY_TO_PUBLISH", "source_tree": "CLEAN",
        "source_provenance": "PUSHED", "source_repo": manifest["source_repo"],
        "source_remote_ref": record.get("source_remote_ref"),
        "source_commit": manifest["source_commit"], "source_tree_hash": manifest["source_tree_hash"],
        "target_series_build": "PASS", "version_safety": "SAFE", "verification_result": verification,
        "verification_scope": record.get("verification_scope"), "verification_reason": record.get("verification_reason"),
        "patch_and_decision_docs": "COMPLETE", "peer_notice": record["peer_notice"],
        "publish": {"operation": "switch", "distribution": args.distribution, "prefix": args.prefix,
                    "snapshot": args.snapshot},
        "build_manifest": {"file": str(manifest_path.relative_to(root)), "sha256": digest(manifest_path)},
        "evidence_manifest": {"file": str(evidence_manifest_path.relative_to(root)), "sha256": digest(evidence_manifest_path)},
    }
    gate_path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(gate_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
