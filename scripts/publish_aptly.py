#!/usr/bin/env python3
"""Publish only the snapshot named by a committed, provenance-checked gate."""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def fail(message):
    print(f"publish-aptly: {message}", file=sys.stderr)
    return 2


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def tracked_clean(repo, path):
    try:
        rel = str(path.relative_to(repo))
        git(repo, "ls-files", "--error-unmatch", rel)
        return not git(repo, "status", "--porcelain", "--", rel)
    except (OSError, ValueError, subprocess.CalledProcessError):
        return False


def run_aptly(args):
    return subprocess.run(["aptly", *args], check=False, capture_output=True, text=True)


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("checked_at must be an ISO-8601 timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("checked_at must include a timezone")
    return parsed.astimezone(timezone.utc)


def apt_candidate(package):
    result = subprocess.run(["apt-cache", "policy", package], check=False, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"apt-cache policy failed: {result.stderr.strip()}")
    match = re.search(r"(?m)^\s*Candidate:\s*(\S+)\s*$", result.stdout)
    if not match:
        raise ValueError("apt-cache policy returned no Candidate version")
    return match.group(1), result.stdout


def write_once_record(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o444)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def log_event(event, package, version, task_id):
    path = Path.home() / "AGENTS-LOG.md"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    with path.open("a", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(f"{stamp} {event} aptly publish {package} {version} ({task_id})\n")
        stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    gate_path = args.gate.resolve()
    try:
        gate_path.relative_to(root)
    except ValueError:
        return fail("gate must be inside this repository")
    if not tracked_clean(root, gate_path):
        return fail("release gate must be tracked, committed, and clean")
    try:
        root_head = git(root, "rev-parse", "HEAD")
        root_remote = git(root, "branch", "-r", "--contains", root_head)
    except (OSError, subprocess.CalledProcessError) as exc:
        return fail(f"cannot inspect gate repository commit: {exc}")
    if not root_remote:
        return fail("gate repository commit is not present in a remote-tracking branch")
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read release gate: {exc}")
    if not isinstance(gate, dict) or gate.get("schema") != 1:
        return fail("unsupported release gate schema")
    required = {"task_state": "READY_TO_PUBLISH", "source_tree": "CLEAN", "target_series_build": "PASS",
                "version_safety": "SAFE", "patch_and_decision_docs": "COMPLETE",
                "source_provenance": "PUSHED"}
    for key, value in required.items():
        if gate.get(key) != value:
            return fail(f"{key} must be {value}")
    verification = gate.get("verification_result")
    if verification == "NOT_APPLICABLE":
        if gate.get("verification_scope") != "MECHANICAL_PACKAGING_ONLY" or not gate.get("verification_reason"):
            return fail("NOT_APPLICABLE requires a mechanical-only scope and reason")
    elif verification != "PASS":
        return fail("verification_result must be PASS or documented NOT_APPLICABLE")
    task_id, package, version = gate.get("task_id"), gate.get("package"), gate.get("candidate_version")
    if not isinstance(task_id, str) or not re.fullmatch(r"UNITY-\d{8}-\d{3,}", task_id):
        return fail("invalid task_id")
    if not isinstance(package, str) or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", package):
        return fail("invalid source package")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9.+:~_-]+", version):
        return fail("invalid candidate version")
    record_path = Path.home() / "coordinator/publish-records" / f"{task_id}.json"
    try:
        record_path.parent.mkdir(parents=True, exist_ok=True)
        publish_lock = record_path.with_suffix(".lock").open("a+")
        fcntl.flock(publish_lock, fcntl.LOCK_EX)
    except OSError as exc:
        return fail(f"cannot lock this task's publication record: {exc}")
    if record_path.exists():
        return fail(f"write-once publish record already exists; inspect it before any repeat publication: {record_path}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(gate.get("target_series", ""))):
        return fail("invalid target_series")
    if gate.get("peer_notice") not in {"ACK", "COORDINATOR_CONFIRMED_NO_CONFLICT"}:
        return fail("peer_notice must be ACK or COORDINATOR_CONFIRMED_NO_CONFLICT")

    board = Path.home() / "coordinator/TASKS.md"
    if not board.is_file(): return fail("private task board is unavailable; cannot verify authoritative state")
    try:
        board_rows = [line for line in board.read_text(encoding="utf-8").splitlines() if len(line.strip("|").split("|")) > 1 and line.strip("|").split("|")[0].strip() == task_id]
    except OSError as exc: return fail(f"cannot read private task board: {exc}")
    if len(board_rows) != 1 or len(board_rows[0].strip("|").split("|")) < 5:
        return fail("task must have exactly one row on the authoritative task board")
    board_cols = [part.strip() for part in board_rows[0].strip("|").split("|")]
    board_state = board_cols[4]
    if board_state != "READY_TO_PUBLISH": return fail(f"task board state is {board_state}, not READY_TO_PUBLISH")
    if len(board_cols) < 9: return fail("task board row is missing the task evidence pointer")
    task_evidence_path = Path(board_cols[8]).expanduser()
    try: task_evidence = json.loads(task_evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: return fail(f"cannot read taskctl evidence: {exc}")
    if not isinstance(task_evidence, dict): return fail("taskctl evidence must contain a JSON object")
    for key, value in (("task_id", task_id), ("package", package), ("candidate_version", version), ("source_commit", gate.get("source_commit")), ("version_safety", "SAFE")):
        if task_evidence.get(key) != value: return fail(f"taskctl evidence does not match publication gate field {key}")
    gate_evidence_path = Path(task_evidence.get("release_gate", ""))
    if not gate_evidence_path.is_absolute(): gate_evidence_path = root / gate_evidence_path
    if gate_evidence_path.resolve() != gate_path: return fail("taskctl evidence points to a different release gate")

    source_repo = Path(gate.get("source_repo", ""))
    if not source_repo.is_absolute(): source_repo = root / source_repo
    source_repo = source_repo.resolve()
    try: source_repo.relative_to((root / "packages").resolve())
    except ValueError: return fail("source repository must be a package checkout under packages/")
    if source_repo.name != package: return fail("source repository directory must match the source package name")
    try:
        commit = git(source_repo, "rev-parse", "HEAD")
        tree = git(source_repo, "rev-parse", "HEAD^{tree}")
        dirty = git(source_repo, "status", "--porcelain")
    except (OSError, subprocess.CalledProcessError) as exc:
        return fail(f"cannot inspect source repository: {exc}")
    if dirty or commit != gate.get("source_commit") or tree != gate.get("source_tree_hash"):
        return fail("source repository cleanliness, commit, and tree hash must match the gate")
    remote_ref = gate.get("source_remote_ref")
    if not isinstance(remote_ref, str) or not remote_ref.strip():
        return fail("source_remote_ref is required")
    full_ref = f"refs/remotes/{remote_ref}"
    try:
        subprocess.run(["git", "-C", str(source_repo), "check-ref-format", full_ref], check=True, capture_output=True)
        git(source_repo, "show-ref", "--verify", "--quiet", full_ref)
        subprocess.run(["git", "-C", str(source_repo), "merge-base", "--is-ancestor", commit, full_ref], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return fail("source commit is not reachable from the specified fetched remote-tracking ref")

    build_ref = gate.get("build_manifest")
    if not isinstance(build_ref, dict) or not isinstance(build_ref.get("file"), str):
        return fail("build_manifest file and hash are required")
    manifest_path = (root / build_ref["file"]).resolve()
    try: manifest_path.relative_to(root)
    except ValueError: return fail("build manifest must be inside the repository")
    if not tracked_clean(root, manifest_path):
        return fail("build manifest must be tracked, committed, and clean")
    if sha256(manifest_path) != build_ref.get("sha256"):
        return fail("build manifest hash does not match the gate")
    try: manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: return fail(f"cannot read build manifest: {exc}")
    for key in ("task_id", "package", "target_series", "candidate_version", "source_commit", "source_tree_hash"):
        manifest_key = "candidate_version" if key == "candidate_version" else key
        if manifest.get(manifest_key) != gate.get(key):
            return fail(f"build manifest does not match gate field {key}")
    if manifest.get("result") != "PASS" or manifest.get("schema") != 1:
        return fail("build manifest is not passing")
    if not isinstance(manifest.get("build_started"), str) or not isinstance(manifest.get("build_finished"), str):
        return fail("build manifest lacks build timestamps")
    log_ref = manifest.get("log", {})
    build_log = manifest_path.parent / str(log_ref.get("file", ""))
    if not build_log.is_file() or sha256(build_log) != log_ref.get("sha256") or not tracked_clean(root, build_log):
        return fail("build log must match its manifest hash and be tracked, committed, and clean")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return fail("build manifest contains no artifacts")
    source_ok = binary_ok = False
    expected_snapshot_names = []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("file"), str):
            return fail("invalid artifact record")
        artifact_path = manifest_path.parent / artifact["file"]
        if not artifact_path.is_file() or sha256(artifact_path) != artifact.get("sha256"):
            return fail(f"artifact hash mismatch: {artifact_path}")
        if artifact.get("kind") == "source":
            source_ok |= artifact.get("package") == package and artifact.get("version") == version
            expected_snapshot_names.append(f"{package}_{version}_source")
        elif artifact.get("kind") == "binary":
            if artifact.get("version") != version: return fail("binary artifact version differs from candidate")
            binary_ok = True
            expected_snapshot_names.append(f"{artifact.get('package')}_{version}_{artifact.get('architecture')}")
    if not source_ok or not binary_ok: return fail("manifest must include the matching source and binary artifacts")

    evidence_ref = gate.get("evidence_manifest")
    if not isinstance(evidence_ref, dict) or not isinstance(evidence_ref.get("file"), str):
        return fail("evidence_manifest file and hash are required")
    evidence_path = (root / evidence_ref["file"]).resolve()
    try: evidence_path.relative_to(root)
    except ValueError: return fail("evidence manifest must be inside the repository")
    if not tracked_clean(root, evidence_path) or sha256(evidence_path) != evidence_ref.get("sha256"):
        return fail("evidence manifest must be tracked, committed, clean, and match its hash")
    try: evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: return fail(f"cannot read evidence manifest: {exc}")
    if not isinstance(evidence, dict) or evidence.get("schema") != 1:
        return fail("unsupported evidence manifest schema")
    for key in ("task_id", "package", "source_commit"):
        if evidence.get(key) != gate.get(key): return fail(f"evidence manifest does not match {key}")
    files = evidence.get("files")
    if not isinstance(files, dict): return fail("evidence manifest files are required")
    required_evidence = {"release_record", "evidence_card", "version_check", "verification_record", "patch_record"}
    if not required_evidence.issubset(files): return fail("evidence manifest is missing required records")
    evidence_files = {}
    for key, item in files.items():
        if not isinstance(item, dict) or not isinstance(item.get("file"), str): return fail(f"evidence.{key} must name a file")
        path = (root / item["file"]).resolve()
        try: path.relative_to(root)
        except ValueError: return fail(f"evidence.{key} must remain inside repository")
        if not path.is_file() or sha256(path) != item.get("sha256") or not tracked_clean(root, path):
            return fail(f"evidence.{key} must match its hash and be tracked, committed, and clean")
        evidence_files[key] = path
    version_check = subprocess.run([sys.executable, str(root / "scripts/version_safety.py"), str(evidence_files["version_check"])],
                                   check=False, capture_output=True, text=True)
    try: version_result = json.loads(version_check.stdout)
    except json.JSONDecodeError: return fail("version-safety executable did not return valid JSON")
    if version_check.returncode != 0 or version_result.get("result") != "SAFE":
        return fail("immediate version-safety recheck is not SAFE")
    if version_result.get("source_package") != package or version_result.get("candidate_source_version") != version:
        return fail("version-safety evidence does not match the package and candidate version")
    if version_result.get("source_commit") != gate.get("source_commit"):
        return fail("version-safety evidence source commit does not match the build")
    if version_result.get("target_series") != gate.get("target_series"):
        return fail("version-safety evidence target series does not match the gate")
    if version_result.get("candidate_binary_version") != version:
        return fail("version-safety binary candidate version does not match the built version")
    built_binary_names = {item.get("package") for item in artifacts if item.get("kind") == "binary"}
    if version_result.get("candidate_binary_package") not in built_binary_names:
        return fail("version-safety apt candidate is not among the built binary artifacts")
    try:
        checked_at = parse_timestamp(version_result.get("checked_at"))
    except (TypeError, ValueError) as exc:
        return fail(f"version evidence freshness cannot be established: {exc}")
    age = datetime.now(timezone.utc) - checked_at
    if age.total_seconds() < -300 or age.total_seconds() > 4 * 60 * 60:
        return fail("version evidence must be no more than four hours old and not more than five minutes in the future")

    publish = gate.get("publish")
    if not isinstance(publish, dict) or publish.get("operation") != "switch":
        return fail("only an explicitly gated aptly publish switch is supported")
    distribution, prefix, snapshot = (publish.get(k) for k in ("distribution", "prefix", "snapshot"))
    if not all(isinstance(v, str) and v and not any(c.isspace() for c in v) for v in (distribution, prefix, snapshot)):
        return fail("publish distribution, prefix, and snapshot must be explicit")
    if ".." in prefix or prefix in {"dists", "pool"}:
        return fail("unsafe aptly prefix")

    shown = run_aptly(["snapshot", "show", "-with-packages", snapshot])
    if shown.returncode: return fail(f"aptly cannot inspect snapshot {snapshot}: {shown.stderr.strip()}")
    for name in expected_snapshot_names:
        if not re.search(rf"(?m)^\s*{re.escape(name)}\s*$", shown.stdout):
            return fail(f"aptly snapshot {snapshot} does not contain expected artifact {name}")

    fresh_policy_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    try:
        fresh_candidate, fresh_policy_output = apt_candidate(version_result["candidate_binary_package"])
    except (OSError, ValueError) as exc:
        return fail(f"fresh local apt-cache policy check failed: {exc}")
    if fresh_candidate != version_result.get("candidate_binary_version"):
        return fail("fresh local apt-cache policy candidate differs from the release candidate")

    try: log_event("START", package, version, task_id)
    except OSError as exc: return fail(f"cannot append publication START event: {exc}")
    command = ["aptly", "publish", "switch", distribution]
    if prefix != ".": command.append(prefix)
    command.append(snapshot)
    try: result = subprocess.run(command, check=False)
    except OSError as exc:
        try: log_event("FAIL(127)", package, version, task_id)
        except OSError: pass
        return fail(f"could not start aptly: {exc}")
    if result.returncode:
        try: log_event(f"FAIL({result.returncode})", package, version, task_id)
        except OSError: pass
        return result.returncode
    published = run_aptly(["publish", "show", distribution, prefix] if prefix != "." else ["publish", "show", distribution])
    if published.returncode or not re.search(rf"(?m)^\s*\w+:\s+{re.escape(snapshot)}\s+\[snapshot\]", published.stdout):
        try: log_event("FAIL(post-publication verification)", package, version, task_id)
        except OSError: pass
        return fail("aptly returned success but publish show does not name the gated snapshot")
    record = {
        "schema": 1,
        "task_id": task_id,
        "package": package,
        "candidate_version": version,
        "source_commit": gate.get("source_commit"),
        "gate_file": str(gate_path.relative_to(root)),
        "gate_sha256": sha256(gate_path),
        "snapshot": snapshot,
        "distribution": distribution,
        "prefix": prefix,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "aptly_result": "PASS",
        "post_publish_check": "PASS",
        "version_evidence_checked_at": version_result.get("checked_at"),
        "fresh_apt_policy": {
            "checked_at": fresh_policy_at,
            "package": version_result["candidate_binary_package"],
            "candidate_version": fresh_candidate,
            "result": "PASS",
            "policy_output": fresh_policy_output,
        },
        "artifacts": [{"file": item["file"], "sha256": item["sha256"], "kind": item["kind"],
                       "package": item.get("package"), "version": item.get("version"),
                       "architecture": item.get("architecture")} for item in artifacts],
    }
    try:
        write_once_record(record_path, record)
    except OSError as exc:
        try: log_event("FAIL(publish record write)", package, version, task_id)
        except OSError: pass
        return fail(f"publication succeeded, but immutable publish record could not be written; do not rerun blindly: {exc}")
    try: log_event("DONE", package, version, task_id)
    except OSError as exc: return fail(f"publication succeeded but final activity log failed: {exc}")
    print(f"published {package} {version}; write-once record: {record_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
