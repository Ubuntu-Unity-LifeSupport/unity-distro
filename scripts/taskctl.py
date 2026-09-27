#!/usr/bin/env python3
"""Locked task-board editor with owner checks, leases, and transition gates."""

import argparse
import hashlib
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys

STATES = {
    "BACKLOG", "CLAIMED", "INVESTIGATING", "READY_FOR_FIX", "IMPLEMENTING",
    "VERIFYING", "REVIEW", "READY_TO_PUBLISH", "PUBLISHED", "DONE",
    "ALREADY_FIXED", "NOT_REPRODUCED", "NOT_APPLICABLE", "DEFERRED",
    "BLOCKED", "REJECTED", "DUPLICATE",
}
CLOSED = {"ALREADY_FIXED", "NOT_REPRODUCED", "NOT_APPLICABLE", "DEFERRED", "REJECTED", "DUPLICATE", "DONE"}
NEXT = {
    "BACKLOG": {"CLAIMED", "DEFERRED", "NOT_APPLICABLE", "DUPLICATE"},
    "CLAIMED": {"INVESTIGATING", "BLOCKED", "DEFERRED"},
    "INVESTIGATING": {"READY_FOR_FIX", "ALREADY_FIXED", "NOT_REPRODUCED", "NOT_APPLICABLE", "DEFERRED", "BLOCKED", "DUPLICATE"},
    "READY_FOR_FIX": {"IMPLEMENTING", "BLOCKED", "DEFERRED"},
    "IMPLEMENTING": {"VERIFYING", "BLOCKED"},
    "VERIFYING": {"REVIEW", "READY_TO_PUBLISH", "IMPLEMENTING", "BLOCKED", "DONE"},
    "REVIEW": {"READY_TO_PUBLISH", "IMPLEMENTING", "BLOCKED"},
    "READY_TO_PUBLISH": {"PUBLISHED", "BLOCKED"},
    "PUBLISHED": {"DONE", "BLOCKED"},
    "BLOCKED": {"CLAIMED", "INVESTIGATING", "READY_FOR_FIX", "IMPLEMENTING", "VERIFYING", "REVIEW", "READY_TO_PUBLISH", "PUBLISHED"},
}


def now():
    return datetime.now(timezone.utc)


def stamp(value=None):
    return (value or now()).strftime("%Y-%m-%d %H:%MZ")


def fail(message):
    print(f"taskctl: {message}", file=sys.stderr)
    return 2


def board_path():
    return Path(os.environ.get("TASKCTL_BOARD", str(Path.home() / "coordinator/TASKS.md"))).expanduser()


def split_row(line):
    return [part.strip() for part in line.strip().strip("|").split("|")]


def read_board(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    header = None
    rows = {}
    for index, line in enumerate(lines):
        if line.startswith("| ID |"):
            header = index
            continue
        if header is not None and line.startswith("|"):
            cols = split_row(line)
            if cols and re.fullmatch(r"UNITY-\d{8}-\d{3,}", cols[0]):
                rows[cols[0]] = (index, cols)
    if header is None:
        raise ValueError("task board has no task table")
    return lines, header, rows


def write_row(lines, index, cols):
    lines[index] = "| " + " | ".join(cols) + " |"


def save_board(path, lines):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def actor_owner(actor):
    return actor in {"A", "B", "C", "May"}


def evidence_for(task_id, supplied):
    path = (Path(supplied).expanduser() if supplied else Path.home() / "coordinator/evidence" / f"{task_id}.json").resolve()
    if not path.is_file():
        raise ValueError(f"machine-readable evidence is required: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("task_id") != task_id:
        raise ValueError("evidence JSON must be an object with the matching task_id")
    return path, data


def non_placeholder(data, *keys):
    placeholders = {"", "unknown", "n/a", "na", "none", "tbd", "todo", "not known", "not applicable"}
    invalid = [key for key in keys if not isinstance(data.get(key), str) or data[key].strip().lower() in placeholders]
    if invalid:
        raise ValueError(f"these fields must contain substantive evidence, not placeholders: {', '.join(invalid)}")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_switch_time_evidence(record):
    """The publisher's switch-time version check (scripts/publish_aptly.py
    publication_evidence) must be a SAFE verdict on a full apt view of the
    published snapshot for this package and version."""
    check, view = record.get("switch_time_version_check"), record.get("switch_time_apt_view")
    if (not isinstance(check, dict) or check.get("result") != "SAFE"
            or check.get("source_package") != record.get("package")
            or check.get("candidate_source_version") != record.get("candidate_version")
            or not check.get("checked_at")):
        raise ValueError("publish record lacks a SAFE switch-time version check for this package and version")
    if (not isinstance(view, dict) or view.get("tool") != "apt_view.py" or view.get("mode") != "full"
            or (view.get("snapshot") or {}).get("name") != record.get("snapshot")):
        raise ValueError("publish record lacks the switch-time apt view of the published snapshot")


def require_evidence(target, data, task_id):
    required = {
        "READY_FOR_FIX": ("reproduction", "reproduction_result", "existing_fix_result", "issue_search_result", "root_cause", "invariant", "chosen_approach"),
        "IMPLEMENTING": ("implementation_plan",),
        "REVIEW": ("verification_record",),
        "READY_TO_PUBLISH": ("release_gate", "build_manifest", "version_check", "verification_record"),
        "PUBLISHED": ("target_verification_record",),
        "DONE": ("terminal_evidence",),
        "BLOCKED": ("blocked_reason", "resume_state"),
        "ALREADY_FIXED": ("existing_fix_result", "existing_fix_evidence"),
        "NOT_REPRODUCED": ("reproduction_record",),
        "NOT_APPLICABLE": ("reason", "evidence_reference"),
        "DEFERRED": ("reason",),
        "REJECTED": ("reason",),
        "DUPLICATE": ("duplicate_of", "evidence_reference"),
    }.get(target, ())
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise ValueError(f"{target} requires evidence fields: {', '.join(missing)}")
    if target == "VERIFYING":
        if data.get("package_change") is True and (not data.get("regression_test") or not data.get("build_manifest")):
            raise ValueError("package verification requires regression_test and build_manifest evidence")
        if data.get("package_change") is False and not data.get("validation_record"):
            raise ValueError("documentation/research verification requires validation_record")
    if target == "BLOCKED" and data.get("resume_state") not in NEXT:
        raise ValueError("BLOCKED requires resume_state to name a resumable process state")
    if target == "READY_FOR_FIX":
        if data.get("reproduction_result") != "PASS":
            raise ValueError("READY_FOR_FIX requires reproduction_result=PASS")
        if data.get("existing_fix_result") not in {"NOT_FIXED", "UNKNOWN"}:
            raise ValueError("READY_FOR_FIX requires a recorded existing-fix outcome; UNKNOWN cannot authorize implementation")
        if data.get("existing_fix_result") != "NOT_FIXED":
            raise ValueError("UNKNOWN existing-fix status cannot advance to READY_FOR_FIX")
        if type(data.get("architectural_task")) is not bool or type(data.get("design_challenger_required")) is not bool:
            raise ValueError("READY_FOR_FIX requires explicit boolean architectural_task and design_challenger_required fields")
        if data.get("architectural_task") and not data.get("design_challenger_required"):
            raise ValueError("architectural_task=true requires design_challenger_required=true")
        if data.get("design_challenger_required") is True and data.get("design_review_result") != "APPROVE":
            raise ValueError("this task requires design_review_result=APPROVE before READY_FOR_FIX")
        if data.get("issue_search_result") not in {"FOUND", "NOT_FOUND"}:
            raise ValueError("issue_search_result must be FOUND or NOT_FOUND")
        non_placeholder(data, "root_cause", "root_cause_mechanism", "root_cause_evidence",
                       "invariant", "chosen_approach", "correct_layer")
        if data.get("architectural_task") is True or data.get("design_challenger_required") is True:
            if data.get("design_challenger_required") is not True or data.get("design_review_result") != "APPROVE":
                raise ValueError("architectural tasks require Design Challenger approval before READY_FOR_FIX")
    if target == "IMPLEMENTING" and data.get("verification_result") == "FAIL" and not data.get("failure_findings"):
        raise ValueError("a rejected patch requires failure_findings before implementation resumes")
    if target == "ALREADY_FIXED" and data.get("existing_fix_result") not in {"FIXED_LOCAL", "FIXED_IN_TARGET_UBUNTU", "FIXED_IN_NEWER_UBUNTU", "FIXED_IN_DEBIAN", "FIXED_UPSTREAM", "PATCH_ALREADY_EXISTS"}:
        raise ValueError("ALREADY_FIXED requires a validated positive existing-fix outcome")
    if target == "REVIEW":
        if data.get("verification_result") not in {"PASS", "FAIL", "INCOMPLETE"}:
            raise ValueError("verification_result must be PASS, FAIL, or INCOMPLETE")
        if data.get("review_status") not in {"REVIEWED", "INDEPENDENTLY_REPRODUCED"}:
            raise ValueError("review_status must distinguish REVIEWED from INDEPENDENTLY_REPRODUCED")
        if data.get("independent_reproduction_required") is True and data.get("review_status") != "INDEPENDENTLY_REPRODUCED":
            raise ValueError("this task requires independent before/after reproduction")
    if target == "PUBLISHED":
        record_path = Path.home() / "coordinator/publish-records" / f"{task_id}.json"
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"publisher-created record is required at {record_path}: {exc}")
        if not isinstance(record, dict) or record.get("schema") != 1:
            raise ValueError("publish record has unsupported schema")
        gate_ref = data.get("release_gate")
        if not isinstance(gate_ref, str):
            raise ValueError("PUBLISHED evidence must point to the release_gate")
        repo = Path(__file__).resolve().parents[1]
        gate_path = Path(gate_ref).expanduser()
        if not gate_path.is_absolute():
            gate_path = repo / gate_path
        gate_path = gate_path.resolve()
        try:
            gate_path.relative_to(repo)
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot validate release gate for publication record: {exc}")
        if not isinstance(gate, dict) or gate.get("schema") != 1 or gate.get("task_state") != "READY_TO_PUBLISH":
            raise ValueError("release gate is not a supported READY_TO_PUBLISH gate")
        if record.get("gate_sha256") != sha256(gate_path):
            raise ValueError("publish record gate hash does not match the release gate")
        if record.get("gate_file") != str(gate_path.relative_to(repo)):
            raise ValueError("publish record names a different release gate")
        for key in ("task_id", "package", "candidate_version", "source_commit"):
            if record.get(key) != gate.get(key) or data.get(key) != gate.get(key):
                raise ValueError(f"publish record and task evidence must match gate field {key}")
        publish = gate.get("publish")
        if not isinstance(publish, dict):
            raise ValueError("release gate has no publish configuration")
        for record_key, gate_key in (("snapshot", "snapshot"), ("distribution", "distribution"), ("prefix", "prefix")):
            if not isinstance(record.get(record_key), str) or not record[record_key] or record.get(record_key) != publish.get(gate_key):
                raise ValueError(f"publish record does not match gate publish.{gate_key}")
        if record.get("aptly_result") != "PASS" or record.get("post_publish_check") != "PASS":
            raise ValueError("publish record must contain successful Aptly and post-publication checks")
        build_ref = gate.get("build_manifest", {})
        if not isinstance(build_ref, dict) or not isinstance(build_ref.get("file"), str):
            raise ValueError("release gate lacks a valid build manifest reference")
        build_path = (repo / build_ref.get("file", "")).resolve()
        try:
            build_path.relative_to(repo)
            build = json.loads(build_path.read_text(encoding="utf-8"))
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot validate build manifest from release gate: {exc}")
        if sha256(build_path) != build_ref.get("sha256"):
            raise ValueError("build manifest hash does not match release gate")
        if not isinstance(build, dict):
            raise ValueError("build manifest is not a JSON object")
        build_artifacts = build.get("artifacts")
        if not isinstance(build_artifacts, list) or not all(isinstance(item, dict) for item in build_artifacts):
            raise ValueError("build manifest has an invalid artifacts list")
        expected_artifacts = [{key: item.get(key) for key in ("file", "sha256", "kind", "package", "version", "architecture")}
                              for item in build_artifacts]
        if record.get("artifacts") != expected_artifacts:
            raise ValueError("publish record artifacts do not match the gated build manifest")
        check_switch_time_evidence(record)
        try:
            published_at = datetime.fromisoformat(record["published_at"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, ValueError):
            raise ValueError("publish record must contain an ISO-8601 published_at timestamp")
        if published_at.tzinfo is None:
            raise ValueError("publish record timestamp must include a timezone")
        if data.get("target_verified") is not True:
            raise ValueError("PUBLISHED requires target_verified=true after target verification")
        target_record = Path(data["target_verification_record"]).expanduser()
        if not target_record.is_absolute():
            target_record = repo / target_record
        if not target_record.is_file():
            raise ValueError("target_verification_record must point to an existing verification record")
        publication = publish.get("distribution")
        prefix = publish.get("prefix")
        command = ["aptly", "publish", "show", publication]
        if prefix != ".":
            command.append(prefix)
        shown = subprocess.run(command, check=False, capture_output=True, text=True)
        if shown.returncode or not re.search(rf"(?m)^\s*\w+:\s+{re.escape(record['snapshot'])}\s+\[snapshot\]", shown.stdout):
            raise ValueError("live aptly publish show does not confirm the recorded snapshot")
    if target == "DONE" and data.get("package_change") is True:
        raise ValueError("package tasks reach DONE only after PUBLISHED")
    if target == "READY_TO_PUBLISH":
        if data.get("version_safety") != "SAFE":
            raise ValueError("READY_TO_PUBLISH requires version_safety=SAFE")
        gate_ref = data.get("release_gate")
        if not isinstance(gate_ref, str): raise ValueError("release_gate must be a repository-relative path")
        gate_path = Path(gate_ref).expanduser()
        if not gate_path.is_absolute(): gate_path = Path(__file__).resolve().parents[1] / gate_path
        gate_path = gate_path.resolve()
        try: gate_path.relative_to(Path(__file__).resolve().parents[1])
        except ValueError: raise ValueError("release_gate must stay inside the repository")
        try: gate = json.loads(gate_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise ValueError(f"cannot read release gate: {exc}")
        for key in ("task_id", "package", "candidate_version", "source_commit"):
            if gate.get(key) != data.get(key): raise ValueError(f"release gate does not match task evidence field {key}")
        if gate.get("task_state") != "READY_TO_PUBLISH" or gate.get("version_safety") != "SAFE":
            raise ValueError("release gate is not in passing publication state")
        build_ref = gate.get("build_manifest", {}).get("file")
        if data.get("build_manifest") != build_ref:
            raise ValueError("release gate build manifest differs from task evidence")
        if gate.get("verification_result") != data.get("verification_result"):
            raise ValueError("release gate verifier result differs from task evidence")
        if data.get("verification_result") == "NOT_APPLICABLE":
            if data.get("verification_scope") != "MECHANICAL_PACKAGING_ONLY" or not data.get("verification_reason"):
                raise ValueError("NOT_APPLICABLE requires a mechanical-only scope and reason")
        elif data.get("verification_result") != "PASS":
            raise ValueError("READY_TO_PUBLISH requires verification_result=PASS or documented NOT_APPLICABLE")


def main():
    parser = argparse.ArgumentParser(prog="taskctl")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create"); p.add_argument("title"); p.add_argument("--actor", required=True)
    p = sub.add_parser("assign"); p.add_argument("task_id"); p.add_argument("owner", choices=["A", "B", "C", "May"]); p.add_argument("machine"); p.add_argument("--actor", required=True)
    p = sub.add_parser("claim"); p.add_argument("task_id"); p.add_argument("--actor", required=True)
    p = sub.add_parser("heartbeat"); p.add_argument("task_id"); p.add_argument("--actor", required=True)
    p = sub.add_parser("transition"); p.add_argument("task_id"); p.add_argument("state", choices=sorted(STATES)); p.add_argument("--actor", required=True); p.add_argument("--evidence")
    p = sub.add_parser("inspect"); p.add_argument("task_id")
    p = sub.add_parser("release"); p.add_argument("task_id"); p.add_argument("--actor", required=True); p.add_argument("--confirmed-idle", action="store_true")
    args = parser.parse_args()
    path = board_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lockpath = path.with_suffix(path.suffix + ".lock")
    with lockpath.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            lines, header_index, rows = read_board(path)
            if args.command == "create":
                if args.actor not in {"C", "May"}: return fail("only C or May creates and allocates task IDs")
                day = now().strftime("%Y%m%d")
                numbers = [int(m.group(1)) for task_id in rows if (m := re.fullmatch(rf"UNITY-{day}-(\d{{3,}})", task_id))]
                task_id = f"UNITY-{day}-{max(numbers, default=0) + 1:03d}"
                cols = [task_id, args.title, "UNASSIGNED", "-", "BACKLOG", "-", "-", stamp(), "-" ]
                insert_at = next((i for i, line in enumerate(lines) if line.strip() == "## Closed tasks"), len(lines))
                if insert_at > 0 and lines[insert_at - 1].strip(): lines.insert(insert_at, "")
                lines.insert(insert_at, "| " + " | ".join(cols) + " |")
                save_board(path, lines)
                print(task_id); return 0
            if args.task_id not in rows:
                return fail(f"unknown task: {args.task_id}")
            index, cols = rows[args.task_id]
            # Current board columns: ID, Title, Owner, Machine, State, Claimed, Lease, Updated, Evidence.
            if args.command == "inspect":
                print(" | ".join(cols)); return 0
            owner, state = cols[2], cols[4]
            actor = getattr(args, "actor", None)
            if args.command == "assign":
                if args.actor not in {"C", "May"}: return fail("only C or May may assign/reassign owners")
                if state not in {"BACKLOG", "BLOCKED"} or owner != "UNASSIGNED": return fail("assignment only accepts unassigned BACKLOG tasks")
                expected_machine = {"A": "target-desktop", "B": "target-desktop-2", "C": "-", "May": "-"}[args.owner]
                if args.machine != expected_machine and not (args.machine == "oem-test" and args.owner in {"A", "B"}): return fail(f"{args.owner} must use {expected_machine}; oem-test needs explicit May assignment")
                cols[2:7] = [args.owner, args.machine, "CLAIMED", stamp(), stamp(now() + timedelta(hours=8))]
            elif args.command == "release":
                if args.actor not in {"C", "May"}: return fail("only C or May may unassign/reassign an owner")
                if not args.confirmed_idle: return fail("release requires --confirmed-idle after checking status and activity log")
                if state in CLOSED or state in {"PUBLISHED", "READY_TO_PUBLISH"}: return fail("cannot release a closed or publication-stage task")
                cols[2], cols[3], cols[4], cols[5], cols[6], cols[7] = "UNASSIGNED", "-", "BACKLOG", "-", "-", stamp()
            elif args.command in {"claim", "heartbeat", "transition"}:
                if owner != actor: return fail(f"task owner is {owner}; actor {actor} cannot change it")
                if args.command == "claim":
                    if state != "CLAIMED": return fail("claim requires the task to be assigned in CLAIMED state")
                    cols[4], cols[5] = "INVESTIGATING", stamp()
                    cols[6] = stamp(now() + timedelta(hours=8))
                elif args.command == "heartbeat":
                    if state in CLOSED: return fail("closed tasks have no renewable lease")
                    cols[6], cols[7] = stamp(now() + timedelta(hours=8)), stamp()
                else:
                    target = args.state
                    allowed = NEXT.get(state, set())
                    if target not in allowed: return fail(f"transition {state} -> {target} is not allowed")
                    if target == "BLOCKED" and state == "BLOCKED": return fail("task is already blocked")
                    evidence_path, data = evidence_for(args.task_id, args.evidence)
                    if state == "BLOCKED" and target != data.get("resume_state"):
                        return fail("a blocked task may resume only at its recorded resume_state")
                    if target == "DONE" and state == "VERIFYING" and data.get("package_change") is not False:
                        return fail("only an explicitly non-package task may move VERIFYING -> DONE")
                    require_evidence(target, data, args.task_id)
                    cols[4], cols[7] = target, stamp()
                    cols[8] = str(evidence_path)
                    if target in CLOSED:
                        cols[6] = "-"
                    else:
                        cols[6] = stamp(now() + timedelta(hours=8))
            write_row(lines, index, cols)
            if cols[4] in CLOSED:
                closed_heading = next((i for i, line in enumerate(lines) if line.strip() == "## Closed tasks"), None)
                if closed_heading is None: return fail("task board has no Closed tasks section")
                header_text = "| ID | Title / package | Owner | Machine / resource | State | Claimed (UTC) | Lease until (UTC) | Updated (UTC) | Evidence |"
                insert = closed_heading + 1
                if insert >= len(lines) or not lines[insert].startswith("| ID |"):
                    lines[insert:insert] = ["", header_text, "|---|---|---|---|---|---|---|---|---|"]
                    insert += 3
                else:
                    insert += 2
                    while insert < len(lines) and split_row(lines[insert])[0].startswith("UNITY-"):
                        insert += 1
                if index < insert: insert -= 1
                row = lines.pop(index)
                lines.insert(insert, row)
            save_board(path, lines)
            print(" | ".join(cols))
            return 0
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
