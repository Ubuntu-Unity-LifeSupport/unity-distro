#!/usr/bin/env python3
"""C's publication approval record (permission model phase 4, design record
docs/research/permission-model-2026-10-09/phase4-publication-authority.md).

`taskctl.py approve-publication` writes ~/coordinator/publication-approvals/
<task>.json; `publish_aptly.py` reads it, consumes it into used/ before aptly
runs, and records its outcome; `taskctl.py` PUBLISHED checks the used copy.
The record is a workflow record written by one OS user for another session
of the same user: it binds the publication to a task, a branch, a commit, a
gate and its artifacts, it does not authenticate anybody.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path.home() / "coordinator" / "publication-approvals"
USED_DIR = "used"
KEYS = frozenset({
    "schema", "kind", "task_id", "approved_by", "approved_at", "not_after", "branch", "gate_file",
    "gate_sha256", "gate_commit", "package", "candidate_version", "source_repo", "source_commit",
    "source_tree_hash", "snapshot", "distribution", "prefix", "build_manifest_sha256",
    "evidence_manifest_sha256", "artifacts", "known_gaps", "first_publication", "may_reference"})
USED_KEYS = KEYS | {"outcome", "consumed_at"}
KIND = "publication-approval"
TASK_RE = re.compile(r"UNITY-\d{8}-\d{3,}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
STAMP_RE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
BRANCH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9/._-]*")
WINDOW = timedelta(hours=4)
FUTURE_SLACK = timedelta(minutes=5)
MAX_SIZE = 256 * 1024
# The scripts the publisher executes or imports from the task worktree, plus
# taskctl.py, which the owner runs there for READY_TO_PUBLISH and PUBLISHED.
# Their blobs at the approved commit must equal origin/main's (design, round 3-5).
PUBLICATION_TOOLS = ("scripts/publish_aptly.py", "scripts/approval_record.py", "scripts/tested_build.py",
                     "scripts/build_dependencies.py", "scripts/version_safety.py", "scripts/apt_view.py",
                     "scripts/taskctl.py",
                     # permission model phase 5: the publisher runs these at the switch
                     "scripts/signer_client.py", "scripts/gpg_standin.py", "signer/signer_core.py")


class ApprovalError(ValueError):
    """A record that must not be acted on; the message names the field."""


def stamp(moment):
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_stamp(value, what):
    if not isinstance(value, str) or not STAMP_RE.fullmatch(value):
        raise ApprovalError(f"{what} must be YYYY-MM-DDTHH:MM:SSZ")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def root():
    return ROOT


def path_for(task_id):
    if not isinstance(task_id, str) or not TASK_RE.fullmatch(task_id):
        raise ApprovalError("task_id must be UNITY-YYYYMMDD-NNN")
    return root() / f"{task_id}.json"


def used_dir():
    return root() / USED_DIR


def _ensure_dir(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def _no_control(text):
    return all(ch >= " " or ch in "\n\t" for ch in text)


def _load(raw, what):
    """Strict JSON: UTF-8, no control characters in strings, one object, no
    null, no duplicate keys, no NaN/Infinity."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ApprovalError(f"{what} must be UTF-8")

    def pairs(items):
        keys = [k for k, _ in items]
        if len(keys) != len(set(keys)):
            raise ApprovalError(f"{what} has duplicate keys")
        return dict(items)

    def constant(name):
        raise ApprovalError(f"{what} contains {name}")

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except ValueError as exc:
        raise ApprovalError(f"{what} is not valid JSON: {exc}")

    def walk(item):
        if item is None:
            raise ApprovalError(f"{what} contains null")
        if isinstance(item, str) and not _no_control(item):
            raise ApprovalError(f"{what} contains a control character")
        if isinstance(item, dict):
            for key, inner in item.items():
                walk(key)
                walk(inner)
        elif isinstance(item, list):
            for inner in item:
                walk(inner)
    walk(value)
    if type(value) is not dict:
        raise ApprovalError(f"{what} must be one JSON object")
    return value


def _read_file(path, what):
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        raise ApprovalError(f"{what} does not exist: {path}")
    if not stat.S_ISREG(st.st_mode):
        raise ApprovalError(f"{what} must be a regular file, not a link")
    if st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o600:
        raise ApprovalError(f"{what} must be owned by this user with mode 0600")
    if st.st_size > MAX_SIZE:
        raise ApprovalError(f"{what} is too large")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        return stream.read(MAX_SIZE + 1)


def validate(record, task_id, what, used=False):
    expected = USED_KEYS if used else KEYS
    if set(record) != expected:
        missing, extra = sorted(expected - set(record)), sorted(set(record) - expected)
        raise ApprovalError(f"{what} has the wrong keys (missing {missing}, extra {extra})")
    if record["schema"] != 1 or type(record["schema"]) is not int or record["kind"] != KIND:
        raise ApprovalError(f"{what} has an unsupported schema or kind")
    if record["task_id"] != task_id:
        raise ApprovalError(f"{what} names another task than its file")
    if record["approved_by"] != "C":
        raise ApprovalError(f"{what} must be C's")
    for key in ("gate_sha256", "build_manifest_sha256", "evidence_manifest_sha256"):
        if not isinstance(record[key], str) or not SHA256_RE.fullmatch(record[key]):
            raise ApprovalError(f"{what}: {key} must be a sha256")
    for key in ("gate_commit", "source_commit", "source_tree_hash"):
        if not isinstance(record[key], str) or not COMMIT_RE.fullmatch(record[key]):
            raise ApprovalError(f"{what}: {key} must be a full git object id")
    for key in ("branch", "gate_file", "package", "candidate_version", "source_repo", "snapshot",
                "distribution", "prefix"):
        if not isinstance(record[key], str) or not record[key] or any(c.isspace() for c in record[key]):
            raise ApprovalError(f"{what}: {key} must be a non-empty string without whitespace")
    if not BRANCH_RE.fullmatch(record["branch"]) or ".." in record["branch"]:
        raise ApprovalError(f"{what}: branch is not a valid branch name")
    if not isinstance(record["artifacts"], list) or not record["artifacts"] or any(
            type(a) is not dict or set(a) != {"file", "sha256", "kind"}
            or not all(isinstance(a[k], str) and a[k] for k in ("file", "sha256", "kind"))
            or not SHA256_RE.fullmatch(a["sha256"]) for a in record["artifacts"]):
        raise ApprovalError(f"{what}: artifacts must be a non-empty list of {{file, sha256, kind}}")
    if not isinstance(record["known_gaps"], list) or any(
            not isinstance(g, str) or not TASK_RE.fullmatch(g) for g in record["known_gaps"]):
        raise ApprovalError(f"{what}: known_gaps must be a list of task ids")
    if type(record["first_publication"]) is not bool or not isinstance(record["may_reference"], str):
        raise ApprovalError(f"{what}: first_publication must be a boolean and may_reference a string")
    if record["first_publication"] and not record["may_reference"].strip():
        raise ApprovalError("a first publication of this package needs May's reference in the approval")
    approved_at = parse_stamp(record["approved_at"], "approved_at")
    not_after = parse_stamp(record["not_after"], "not_after")
    if not_after - approved_at != WINDOW:
        raise ApprovalError(f"{what}: the approval window must be exactly {WINDOW}")
    if used:
        if not isinstance(record["outcome"], str) or not record["outcome"]:
            raise ApprovalError(f"{what}: outcome must be a non-empty string")
        parse_stamp(record["consumed_at"], "consumed_at")
    return approved_at, not_after


def read(task_id, now=None):
    """The current approval of task_id: (record, sha256, raw bytes). Refuses an
    expired or future-dated record and anything validate() refuses."""
    path = path_for(task_id)
    if not os.path.lexists(path):
        raise ApprovalError("no publication approval by C; run taskctl.py approve-publication")
    raw = _read_file(path, "the publication approval")
    record = _load(raw, "the publication approval")
    approved_at, not_after = validate(record, task_id, "the publication approval")
    now = now or datetime.now(timezone.utc)
    if approved_at > now + FUTURE_SLACK:
        raise ApprovalError("the publication approval is dated in the future")
    if now >= not_after:
        raise ApprovalError("the publication approval has expired; ask C for a new one")
    return record, hashlib.sha256(raw).hexdigest(), raw


def read_used(path, task_id):
    """A consumed approval under used/, named by the publish record: (record, sha256)."""
    path = Path(path)
    try:
        path.resolve().relative_to(used_dir().resolve())
    except ValueError:
        raise ApprovalError("the consumed approval must be under publication-approvals/used/")
    raw = _read_file(path, "the consumed approval")
    record = _load(raw, "the consumed approval")
    validate(record, task_id, "the consumed approval", used=True)
    return record, hashlib.sha256(raw).hexdigest()


def _encode(record):
    return (json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _write_private(path, data, exclusive):
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_EXCL if exclusive else os.O_TRUNC)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def write(record):
    """Write the approval atomically with mode 0600; the caller validated it
    and holds the publication lock. Returns its sha256."""
    task_id = record.get("task_id")
    validate(record, task_id, "the new publication approval")
    path = path_for(task_id)
    _ensure_dir(root())
    data = _encode(record)
    tmp = path.with_name(path.name + ".tmp")
    _write_private(tmp, data, exclusive=False)
    os.replace(tmp, path)
    return hashlib.sha256(data).hexdigest()


def remove(task_id):
    path = path_for(task_id)
    if not os.path.lexists(path):
        raise ApprovalError("no publication approval to revoke")
    os.unlink(path)


def consume(task_id, raw, sha, outcome, when=None):
    """Move the validated approval (raw/sha from read()) to used/ with an
    outcome, before aptly runs: re-hash through O_NOFOLLOW, write the used
    copy with O_EXCL and fsync, then unlink the original. Returns
    (used path, sha256 of the used file)."""
    path = path_for(task_id)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        current = stream.read(MAX_SIZE + 1)
    if hashlib.sha256(current).hexdigest() != sha or current != raw:
        raise ApprovalError("the publication approval changed while the publisher ran; nothing consumed")
    record = _load(raw, "the publication approval")
    record["outcome"] = outcome
    record["consumed_at"] = stamp(when or datetime.now(timezone.utc))
    _ensure_dir(used_dir())
    used = used_dir() / f"{task_id}-{record['consumed_at'].replace(':', '')}.json"
    data = _encode(record)
    _write_private(used, data, exclusive=True)
    os.unlink(path)
    return used, hashlib.sha256(data).hexdigest()


def set_outcome(used, task_id, outcome):
    """Rewrite the outcome of a consumed approval (0600, atomic). Returns the new sha256."""
    used = Path(used)
    record, _ = read_used(used, task_id)
    record["outcome"] = outcome
    data = _encode(record)
    tmp = used.with_name(used.name + ".tmp")
    _write_private(tmp, data, exclusive=False)
    os.replace(tmp, used)
    return hashlib.sha256(data).hexdigest()


def known_sources(public_dir, distribution, prefix):
    """Source names of the live publication, from the uncompressed Packages
    index the live Release lists: a file read, never an aptly command. Refuses
    a Release whose components or architectures differ from main / amd64."""
    public = Path(public_dir)
    dist_dir = public / (prefix if prefix != "." else "") / "dists" / distribution
    release = dist_dir / "Release"
    try:
        text = release.read_text(encoding="utf-8")
    except OSError as exc:
        raise ApprovalError(f"cannot read the live Release: {exc}")
    fields = {}
    for line in text.splitlines():
        if line and not line[0].isspace() and ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    if fields.get("Components") != "main" or fields.get("Architectures") != "amd64":
        raise ApprovalError("the live Release lists other components or architectures than main / amd64; "
                            "update known_sources() before approving")
    packages = dist_dir / "main" / "binary-amd64" / "Packages"
    try:
        stanzas = packages.read_text(encoding="utf-8")
    except OSError as exc:
        raise ApprovalError(f"cannot read the live Packages index: {exc}")
    sources = set()
    for stanza in stanzas.split("\n\n"):
        package = source = None
        for line in stanza.splitlines():
            if line.startswith("Package:"):
                package = line.split(":", 1)[1].strip()
            elif line.startswith("Source:"):
                source = line.split(":", 1)[1].strip().split(" ", 1)[0]
        if package:
            sources.add(source or package)
    return sources
