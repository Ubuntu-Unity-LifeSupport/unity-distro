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
    "REVIEW": {"READY_TO_PUBLISH", "IMPLEMENTING", "BLOCKED", "DONE"},
    "READY_TO_PUBLISH": {"PUBLISHED", "BLOCKED"},
    "PUBLISHED": {"DONE", "BLOCKED"},
    "BLOCKED": {"CLAIMED", "INVESTIGATING", "READY_FOR_FIX", "IMPLEMENTING", "VERIFYING", "REVIEW", "READY_TO_PUBLISH", "PUBLISHED"},
}


# UNITY-20260928-005: what a task changes decides its path to DONE
# (ENGINEERING-PROCESS section 1). A mixed task takes the first kind that
# applies in this order.
KINDS = ("package", "tool", "operation", "documentation")
# Evidence that only a package task carries: any of these forces "package".
PACKAGE_MARKERS = ("build_manifest", "release_gate", "candidate_version", "version_safety")
# From READY_FOR_FIX on, every transition needs a resolved kind.
KIND_STATES = {"READY_FOR_FIX", "IMPLEMENTING", "VERIFYING", "REVIEW", "READY_TO_PUBLISH", "PUBLISHED", "DONE"}


def resolve_kind(data):
    """The task's kind from its evidence, or None if it does not say.
    package_change, when present, must be a bool that agrees with task_kind;
    a legacy task with package_change=true and no task_kind is a package;
    package-only evidence forces package."""
    kind, package_change = data.get("task_kind"), data.get("package_change")
    if kind is not None and kind not in KINDS:
        raise ValueError(f"task_kind must be one of {', '.join(KINDS)}")
    if package_change is not None and type(package_change) is not bool:
        raise ValueError("package_change must be true or false")
    markers = [key for key in PACKAGE_MARKERS if data.get(key)]
    if markers and kind not in (None, "package"):
        raise ValueError(f"evidence with {', '.join(markers)} belongs to a package task, not task_kind={kind}")
    if kind is None and (package_change is True or markers):
        kind = "package"
    if kind is not None and package_change is not None and package_change != (kind == "package"):
        raise ValueError(f"package_change={str(package_change).lower()} contradicts task_kind={kind}")
    return kind


def kind_lock_path(task_id):
    """The kind a task is held to, recorded by taskctl beside the evidence
    files of the board it manages."""
    return board_path().parent / "evidence" / f"{task_id}.kind"


def read_kind_lock(path):
    """The locked kind, or None when there is no lock. A lock that does not
    hold exactly one kind (empty, unknown, extra lines) is an error: it must
    never stand in for a kind and let a task past its gates."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if text not in KINDS:
        raise ValueError(f"kind lock {path} holds {text!r}, not one of {', '.join(KINDS)}; repair it before any transition")
    return text


def write_kind_lock(path, kind):
    """Write the lock atomically: a reader sees the old state or the whole kind."""
    if kind not in KINDS:
        raise ValueError(f"refusing to lock unknown kind {kind!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(kind + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


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


# UNITY-20260929-015: a later publication replaces the live snapshot's name;
# the task's publication is still live if the live snapshot carries every
# artifact of the record, byte for byte. Read-only aptly commands only.
PUBLISH_SOURCE = re.compile(r"(?m)^\s*(\w+):\s+(\S+)\s+\[(\w+)\]\s*$")


def run_aptly_read(args):
    return subprocess.run(["aptly"] + args, check=False, capture_output=True, text=True)


def confirm_live_publication(record, distribution, prefix, run=run_aptly_read):
    """None if the record's publication is live now, else the reason it is not.
    Live means: publish show names the record's snapshot, or it names exactly
    one other snapshot that holds every source and binary artifact of the
    record with the recorded version and sha256."""
    shown = run(["publish", "show", distribution] + ([prefix] if prefix != "." else []))
    if shown.returncode:
        return f"aptly publish show {distribution} failed: {shown.stderr.strip()}"
    sources = PUBLISH_SOURCE.findall(shown.stdout)
    if (record["snapshot"], "snapshot") in [(name, kind) for _component, name, kind in sources]:
        return None
    if len(sources) != 1 or sources[0][2] != "snapshot":
        return (f"live publication does not name the recorded snapshot {record['snapshot']} and is not exactly "
                f"one snapshot: {[f'{c}: {n} [{k}]' for c, n, k in sources]}")
    live = sources[0][1]
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from publish_aptly import snapshot_content, PROVENANCE_ONLY_KINDS

    artifacts = record.get("artifacts") or []
    kinds = [a.get("kind") for a in artifacts]
    if kinds.count("source") != 1 or "source_file" not in kinds or "binary" not in kinds:
        return "publish record must list exactly one source, its source files and at least one binary"
    other = sorted({k for k in kinds} - {"source", "source_file", "binary"} - PROVENANCE_ONLY_KINDS, key=str)
    if other:
        return f"publish record has artifact kinds without a live-content rule: {other}"
    missing, differing = snapshot_content(artifacts, live, run)
    if missing or differing:
        return (f"live snapshot {live} (the recorded {record['snapshot']} is no longer live) does not carry the "
                f"record's artifacts: missing {missing}, other sha256 {differing}")
    return None


# UNITY-20260929-023: a package task published as part of another task's
# publication (same package version, one publish record under that task).
_TASK_ID = re.compile(r"^UNITY-\d{8}-\d{3}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def read_publish_record(path, expected_sha256=None):
    """Read a publisher-written record once: no symlink, a regular file with
    no write bit (write_once_record makes it 0444 with O_EXCL); the sha256 and
    the JSON come from the same bytes."""
    import stat
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ValueError(f"publisher-created record is required at {path}: {exc}")
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"publish record {path} is not a regular file")
        if info.st_mode & 0o222:
            raise ValueError(f"publish record {path} is writable; the publisher writes it read-only")
        raw = stream.read()
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"publish record {path} does not have the sha256 named in published_by")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"publish record {path} is not JSON: {exc}")


def covering_record(data, task_id, records_dir):
    """(record, publishing task) named by the evidence's published_by."""
    covered = data.get("published_by")
    if not isinstance(covered, dict) or set(covered) != {"task_id", "record_sha256"}:
        raise ValueError("published_by must be {task_id, record_sha256}")
    other, digest = covered.get("task_id"), covered.get("record_sha256")
    if not isinstance(other, str) or not _TASK_ID.match(other):
        raise ValueError("published_by.task_id must be a full UNITY-YYYYMMDD-NNN task id")
    if not isinstance(digest, str) or not _HEX64.match(digest):
        raise ValueError("published_by.record_sha256 must be 64 hex characters")
    if other == task_id:
        raise ValueError("published_by must name another task; this task's own record is read without it")
    record = read_publish_record(Path(records_dir) / f"{other}.json", digest)
    if not isinstance(record, dict) or record.get("task_id") != other:
        raise ValueError(f"publish record of {other} does not belong to {other}")
    return record, other


def check_own_build(data, task_id, record, repo):
    """The task's own build_sbuild manifest proves its change is in the
    published bytes (UNITY-20261008-003): the same package version, and either
    (1) its source and binary artifacts equal the publish record by file and
    sha256, or (2) it is buildinfo_identical to the published build, which is
    reached through the record's gate: the same source commit and tree, extra
    build dependencies, .buildinfo identity and Installed-Build-Depends, both
    .buildinfo files committed. A commit that is only an ancestor of the
    published one proves nothing about the bytes and is refused."""
    # Verifier round 1: the covered task's own review and build are bound here,
    # because the gate the PUBLISHED check reads is the publishing task's.
    if data.get("task_id") != task_id:
        raise ValueError("the evidence's task_id must be this task")
    if data.get("verification_result") != "PASS" or \
            data.get("review_status") not in {"REVIEWED", "INDEPENDENTLY_REPRODUCED"}:
        raise ValueError("published_by requires this task's own verification_result PASS and review_status")
    ref = data.get("build_manifest")
    if not isinstance(ref, str) or not ref:
        raise ValueError("published_by requires the task's own build_manifest")
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from tested_build import buildinfo_identity_error, committed, dependency_identity, manifest_buildinfo
    path, _rel, _digest, error = committed(repo, ref, "the task's build_manifest")
    if error:
        raise ValueError(error)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read the task's build_manifest {ref}: {exc}")
    if not isinstance(manifest, dict) or manifest.get("task_id") != task_id:
        raise ValueError("the build_manifest named by this task is not this task's build")
    for key in ("package", "candidate_version"):
        if manifest.get(key) != record.get(key):
            raise ValueError(f"the task's build_manifest {key} differs from the publish record")

    # rule 1: the same bytes
    pairs = lambda m: {(a.get("file"), a.get("sha256")) for a in m.get("artifacts") or []
                       if isinstance(a, dict) and a.get("kind") in ("source", "binary")
                       and isinstance(a.get("file"), str) and isinstance(a.get("sha256"), str)}
    listed = [a for a in manifest.get("artifacts") or [] if isinstance(a, dict) and a.get("kind") in ("source", "binary")]
    if not listed:
        raise ValueError("the task's build_manifest lists no source or binary artifacts")
    if any(not isinstance(a.get("file"), str) or not isinstance(a.get("sha256"), str) or not _HEX64.match(a["sha256"])
           for a in listed):
        raise ValueError("every source and binary artifact of the task's build_manifest needs a file and a sha256")
    own, shipped = pairs(manifest), pairs(record)
    if own == shipped:
        return
    byte_reason = f"missing {sorted(own - shipped)}, extra {sorted(shipped - own)}"

    # rule 2: buildinfo_identical to the published build, read through the record's gate
    def refuse(reason):
        raise ValueError("the task's artifacts are not the published bytes (" + byte_reason + ") and its build is not "
                         "buildinfo_identical to the published build: " + reason)
    gate_path, _g, gate_digest, error = committed(repo, record.get("gate_file"), "the publish record's gate_file")
    if error:
        refuse(error)
    if gate_digest != record.get("gate_sha256"):
        refuse("the release gate does not match the publish record's gate_sha256")
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        refuse(f"cannot read the release gate: {exc}")
    if not isinstance(gate, dict) or gate.get("task_id") != record.get("task_id"):
        refuse("the release gate belongs to another task than the publish record")
    build_ref = gate.get("build_manifest")
    if not isinstance(build_ref, dict):
        refuse("the release gate lacks a build manifest reference")
    pub_path, _p, pub_digest, error = committed(repo, build_ref.get("file"), "the published build manifest")
    if error:
        refuse(error)
    if pub_digest != build_ref.get("sha256"):
        refuse("the published build manifest does not match the release gate")
    try:
        published = json.loads(pub_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        refuse(f"cannot read the published build manifest: {exc}")
    if not isinstance(published, dict):
        refuse("the published build manifest is not a JSON object")
    for label, a, b in (("source_commit", manifest.get("source_commit"), published.get("source_commit")),
                        ("source_tree_hash", manifest.get("source_tree_hash"), published.get("source_tree_hash")),
                        ("build_dependencies", dependency_identity(manifest), dependency_identity(published))):
        if a != b or (label != "build_dependencies" and not a):
            refuse(f"the two builds differ in {label}")
    own_text, error = manifest_buildinfo(repo, manifest, path.parent, "task's")
    if error:
        refuse(error)
    pub_text, error = manifest_buildinfo(repo, published, pub_path.parent, "published")
    if error:
        refuse(error)
    error = buildinfo_identity_error(own_text, pub_text, "task's", "published")
    if error:
        refuse(error)


def require_authorization(data):
    """An operation acts on shared infrastructure: who approved it, where
    that approval is recorded, and what it covers."""
    auth = data.get("authorization")
    if not isinstance(auth, dict):
        raise ValueError("operation tasks require authorization {approved_by, reference, scope}")
    if auth.get("approved_by") not in {"May", "C"}:
        raise ValueError("authorization.approved_by must be May or C")
    non_placeholder(auth, "reference", "scope")


def require_evidence(target, data, task_id, kind=None, state=None):
    if kind is None:
        kind = resolve_kind(data)
    if target in ("READY_TO_PUBLISH", "PUBLISHED") and kind != "package":
        raise ValueError(f"only package tasks are published; this task is {kind}")
    defect_card = kind in (None, "package", "tool")
    required = {
        "READY_FOR_FIX": (("reproduction", "reproduction_result", "existing_fix_result", "issue_search_result", "root_cause", "invariant", "chosen_approach")
                          if defect_card else
                          ("scope", "chosen_approach", "existing_state_check") if kind == "operation" else ("scope", "chosen_approach")),
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
        if kind == "package" and (not data.get("regression_test") or not data.get("build_manifest")):
            raise ValueError("package verification requires regression_test and build_manifest evidence")
        if kind == "tool" and (not data.get("regression_test") or not data.get("validation_record")):
            raise ValueError("tool verification requires regression_test and validation_record evidence")
        if kind in ("operation", "documentation") and not data.get("validation_record"):
            raise ValueError(f"{kind} verification requires validation_record")
    if target == "BLOCKED" and data.get("resume_state") not in NEXT:
        raise ValueError("BLOCKED requires resume_state to name a resumable process state")
    if target == "READY_FOR_FIX" and not defect_card:
        if type(data.get("architectural_task")) is not bool or type(data.get("design_challenger_required")) is not bool:
            raise ValueError("READY_FOR_FIX requires explicit boolean architectural_task and design_challenger_required fields")
        if data.get("architectural_task") and not data.get("design_challenger_required"):
            raise ValueError("architectural_task=true requires design_challenger_required=true")
        if data.get("design_challenger_required") is True and data.get("design_review_result") != "APPROVE":
            raise ValueError("this task requires design_review_result=APPROVE before READY_FOR_FIX")
        non_placeholder(data, "scope", "chosen_approach", "correct_layer")
        if kind == "operation":
            non_placeholder(data, "existing_state_check")
            require_authorization(data)
    if target == "READY_FOR_FIX" and defect_card:
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
        records_dir = Path.home() / "coordinator/publish-records"
        repo = Path(__file__).resolve().parents[1]
        covered_by = None
        if "published_by" in data:
            record, covered_by = covering_record(data, task_id, records_dir)
            check_own_build(data, task_id, record, repo)
        else:
            record_path = records_dir / f"{task_id}.json"
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"publisher-created record is required at {record_path}: {exc}")
        if not isinstance(record, dict) or record.get("schema") != 1:
            raise ValueError("publish record has unsupported schema")
        gate_ref = data.get("release_gate")
        if covered_by:
            # The gate is the publishing task's, named by its record.
            if gate_ref and gate_ref != record.get("gate_file"):
                raise ValueError("release_gate and published_by name different gates")
            gate_ref = record.get("gate_file")
        if not isinstance(gate_ref, str):
            raise ValueError("PUBLISHED evidence must point to the release_gate")
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
            if record.get(key) != gate.get(key):
                raise ValueError(f"publish record and task evidence must match gate field {key}")
            # A covered task has its own task id and may record its commit as
            # text; check_own_build tied its build to the published bytes.
            if covered_by and key in ("task_id", "source_commit"):
                continue
            if data.get(key) != gate.get(key):
                raise ValueError(f"publish record and task evidence must match gate field {key}")
        if covered_by and gate.get("task_id") != covered_by:
            raise ValueError("the release gate named by the publish record belongs to another task")
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
        live_error = confirm_live_publication(record, publish.get("distribution"), publish.get("prefix"))
        if live_error:
            raise ValueError(live_error)
    if target == "DONE":
        # UNITY-20260928-005: DONE by kind and by the state it comes from.
        if kind not in KINDS:
            raise ValueError(f"DONE requires a known task kind, not {kind!r}")
        if kind == "package" and state != "PUBLISHED":
            raise ValueError("package tasks reach DONE only after PUBLISHED")
        if kind == "tool" and state != "REVIEW":
            raise ValueError("tool tasks reach DONE only from REVIEW, after the Verifier")
        if kind in ("operation", "documentation") and state not in ("VERIFYING", "REVIEW"):
            raise ValueError(f"{kind} tasks reach DONE from VERIFYING or REVIEW")
        if state == "REVIEW":
            if data.get("verification_result") != "PASS":
                raise ValueError("DONE from REVIEW requires verification_result=PASS")
            if data.get("review_status") not in {"REVIEWED", "INDEPENDENTLY_REPRODUCED"}:
                raise ValueError("DONE from REVIEW requires review_status REVIEWED or INDEPENDENTLY_REPRODUCED")

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


def show_open_alerts():
    """Print alerts nobody has acknowledged yet (scripts/alerts.py) to stderr.

    Automation raises alerts into ALERTS.md next to the board; they stay on
    every taskctl run until C or May acknowledges them. Read-only and
    best-effort: a missing or unreadable file never blocks a board operation."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import alerts
        path = Path(os.environ.get("ALERTS_FILE", str(board_path().parent / "ALERTS.md"))).expanduser()
        pending = alerts.open_alerts(path)
    except Exception:
        return
    if pending:
        print(f"taskctl: {len(pending)} unacknowledged alert(s) in {path}"
              " - C or May: act on it and run scripts/alerts.py ack --actor C|May --key KEY", file=sys.stderr)
        for line in pending:
            print(f"  ALERT {line}", file=sys.stderr)


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
    show_open_alerts()
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
                    kind = resolve_kind(data)
                    lock = kind_lock_path(args.task_id)
                    locked = read_kind_lock(lock)
                    if locked is not None and kind is None:
                        kind = locked
                    if locked is not None and kind != locked:
                        return fail(f"task {args.task_id} is held to task_kind={locked} ({lock}); its evidence now says {kind}")
                    if target in KIND_STATES and kind is None:
                        return fail(f"{target} requires task_kind ({', '.join(KINDS)}) or package_change=true in the evidence")
                    if kind is not None and data.get("package_change") is not None and data.get("package_change") != (kind == "package"):
                        return fail(f"package_change contradicts the task's kind {kind}")
                    require_evidence(target, data, args.task_id, kind, state)
                    if locked is None and kind is not None and target in KIND_STATES:
                        write_kind_lock(lock, kind)
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
