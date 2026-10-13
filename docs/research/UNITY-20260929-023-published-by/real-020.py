#!/usr/bin/env python3
"""UNITY-20260929-023 validation: covering_record and check_own_build on the real
case, UNITY-20260928-020 published by UNITY-20260927-027 (read-only).
Usage: real-020.py <scripts dir> <repo with -020's manifest>"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, sys.argv[1])
import taskctl  # noqa: E402

records = Path.home() / "coordinator/publish-records"
evidence = json.loads((Path.home() / "coordinator/evidence/UNITY-20260928-020.json").read_text())
digest = hashlib.sha256((records / "UNITY-20260927-027.json").read_bytes()).hexdigest()
data = dict(evidence, published_by={"task_id": "UNITY-20260927-027", "record_sha256": digest})
record, other = taskctl.covering_record(data, "UNITY-20260928-020", records)
print(f"record of {other}: {record['package']} {record['candidate_version']} {record['source_commit'][:12]} sha256 {digest[:16]}")
taskctl.check_own_build(data, "UNITY-20260928-020", record, sys.argv[2])
print("check_own_build: PASS (-020's manifest commit, artifacts by name, in the published record)")
bad = dict(data, published_by={"task_id": "UNITY-20260927-027", "record_sha256": "0" * 64})
try:
    taskctl.covering_record(bad, "UNITY-20260928-020", records)
except ValueError as exc:
    print("wrong sha256 refused:", exc)
