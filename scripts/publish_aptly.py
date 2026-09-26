#!/usr/bin/env python3
"""Validate a release-gate record, then run an explicit aptly publish command."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys


REQUIRED_EQUAL = {
    "task_state": "READY_TO_PUBLISH",
    "source_tree": "CLEAN",
    "target_series_build": "PASS",
    "version_safety": "SAFE",
    "patch_and_decision_docs": "COMPLETE",
}
REQUIRED_TEXT = (
    "task_id",
    "package",
    "candidate_version",
    "source_commit",
    "source_repo",
)
REQUIRED_EVIDENCE = (
    "evidence_card",
    "build_log",
    "version_check",
    "verification_record",
)


def fail(message: str) -> int:
    print(f"publish-aptly: {message}", file=sys.stderr)
    return 2


def log_event(event: str, package: str, version: str, task_id: str) -> None:
    path = Path.home() / "AGENTS-LOG.md"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            f"{stamp} {event} aptly publish {package} {version} ({task_id})\n"
        )


def main(argv: list[str]) -> int:
    if "--" not in argv:
        return fail("usage: publish_aptly.py --gate FILE -- aptly publish snapshot|switch ...")
    split = argv.index("--")
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--gate", required=True, help="committed release-gate JSON")
    args = parser.parse_args(argv[:split])
    command = argv[split + 1 :]
    if len(command) < 3 or command[0] != "aptly" or command[1] != "publish":
        return fail("only an explicit `aptly publish snapshot|switch ...` command is accepted")
    if command[2] not in {"snapshot", "switch"}:
        return fail("only `aptly publish snapshot` or `aptly publish switch` is accepted")

    repo_root = Path(__file__).resolve().parents[1]
    gate_input = Path(args.gate)
    gate_path = (repo_root / gate_input).resolve()
    if gate_input.is_absolute():
        gate_path = gate_input.resolve()
    try:
        gate_path.relative_to(repo_root)
    except ValueError:
        return fail("the gate record must be inside the repository")
    gate_relative = str(gate_path.relative_to(repo_root))
    try:
        tracked_gate = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", gate_relative],
            check=False,
            capture_output=True,
            text=True,
        )
        dirty_gate = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain", "--", gate_relative],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        root_head = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        root_remote_branches = subprocess.run(
            ["git", "-C", str(repo_root), "branch", "-r", "--contains", root_head],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return fail(f"cannot inspect the release-gate commit: {exc}")
    if tracked_gate.returncode != 0 or dirty_gate:
        return fail("the release-gate JSON must be tracked and committed")
    if not root_remote_branches:
        return fail("the release-gate commit is not present in a remote-tracking branch")
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read the gate record: {exc}")
    if not isinstance(gate, dict):
        return fail("the gate record must be a JSON object")

    for key, expected in REQUIRED_EQUAL.items():
        if gate.get(key) != expected:
            return fail(f"{key} must be {expected}")
    for key in REQUIRED_TEXT:
        if not isinstance(gate.get(key), str) or not gate[key].strip():
            return fail(f"{key} is required")
    if not re.fullmatch(r"UNITY-\d{8}-\d{3,}", gate["task_id"]):
        return fail("task_id must use UNITY-YYYYMMDD-NNN")
    if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", gate["package"]):
        return fail("package must be a Debian source package name")
    if not re.fullmatch(r"[A-Za-z0-9.+:~_-]+", gate["candidate_version"]):
        return fail("candidate_version must be a single Debian version")
    if gate.get("source_provenance") not in {"PUSHED", "TRACKED_EXPORT"}:
        return fail("source_provenance must be PUSHED or TRACKED_EXPORT")
    if gate.get("built_from_source_commit") != gate.get("source_commit"):
        return fail("built_from_source_commit must exactly match source_commit")
    source_repo = Path(gate["source_repo"])
    if not source_repo.is_absolute():
        source_repo = repo_root / source_repo
    source_repo = source_repo.resolve()
    try:
        current_commit = subprocess.run(
            ["git", "-C", str(source_repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(source_repo), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return fail(f"cannot inspect source repository: {exc}")
    if current_commit != gate["source_commit"]:
        return fail("source_repo HEAD does not match source_commit")
    if dirty:
        return fail("source_repo is not clean")
    if gate["source_provenance"] == "PUSHED":
        remote_ref = gate.get("source_remote_ref")
        if not isinstance(remote_ref, str) or not remote_ref.strip():
            return fail("source_remote_ref is required when source_provenance is PUSHED")
        try:
            pushed = subprocess.run(
                [
                    "git",
                    "-C",
                    str(source_repo),
                    "merge-base",
                    "--is-ancestor",
                    gate["source_commit"],
                    remote_ref,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            return fail(f"cannot check the source remote ref: {exc}")
        if pushed.returncode != 0:
            return fail("source_commit is not present in source_remote_ref")
    if gate.get("peer_notice") not in {
        "ACK",
        "COORDINATOR_CONFIRMED_NO_CONFLICT",
    }:
        return fail("peer_notice must be ACK or COORDINATOR_CONFIRMED_NO_CONFLICT")

    verification = gate.get("verification_result")
    if verification == "PASS":
        pass
    elif (
        verification == "NOT_APPLICABLE"
        and gate.get("verification_scope") == "MECHANICAL_PACKAGING_ONLY"
        and isinstance(gate.get("verification_reason"), str)
        and gate["verification_reason"].strip()
    ):
        pass
    else:
        return fail(
            "verification_result must be PASS, or NOT_APPLICABLE with "
            "MECHANICAL_PACKAGING_ONLY and a reason"
        )

    evidence = gate.get("evidence")
    if not isinstance(evidence, dict):
        return fail("evidence must be an object of repository-relative paths")
    for key in REQUIRED_EVIDENCE:
        value = evidence.get(key)
        if not isinstance(value, str) or not value.strip():
            return fail(f"evidence.{key} is required")
        evidence_path = (repo_root / value).resolve()
        try:
            evidence_path.relative_to(repo_root)
        except ValueError:
            return fail(f"evidence.{key} must stay inside the repository")
        if not evidence_path.is_file():
            return fail(f"evidence file does not exist: {value}")
    if gate["source_provenance"] == "TRACKED_EXPORT":
        exported = evidence.get("source_export")
        if not isinstance(exported, str) or not exported.strip():
            return fail("evidence.source_export is required for TRACKED_EXPORT")
        export_path = (repo_root / exported).resolve()
        try:
            export_path.relative_to(repo_root)
        except ValueError:
            return fail("evidence.source_export must stay inside the repository")
        if not export_path.is_file():
            return fail(f"source export does not exist: {exported}")

    package = gate["package"]
    version = gate["candidate_version"]
    task_id = gate["task_id"]
    try:
        log_event("START", package, version, task_id)
    except OSError as exc:
        return fail(f"cannot append START to ~/AGENTS-LOG.md: {exc}")

    try:
        result = subprocess.run(command, check=False)
    except OSError as exc:
        try:
            log_event("FAIL(127)", package, version, task_id)
        except OSError:
            pass
        return fail(f"could not start aptly: {exc}")
    event = "DONE" if result.returncode == 0 else f"FAIL({result.returncode})"
    try:
        log_event(event, package, version, task_id)
    except OSError as exc:
        return fail(f"aptly returned {result.returncode}; could not append final log: {exc}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
