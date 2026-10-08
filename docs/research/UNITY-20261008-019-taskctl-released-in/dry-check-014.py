#!/usr/bin/env python3
"""dry-check-014.py - read-only: run released_in_record and check_released_commits of this branch's taskctl on
UNITY-20261008-014 with released_in pointing at UNITY-20261008-011's real publish record. No board write, no
transition, no aptly. Prints each check's result."""
import hashlib
import json
from pathlib import Path
import sys

repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo / "scripts"))
import taskctl  # noqa: E402

records = Path.home() / "coordinator/publish-records"
record_path = records / "UNITY-20261008-011.json"
digest = hashlib.sha256(record_path.read_bytes()).hexdigest()
data = json.load(open(Path.home() / "coordinator/evidence/UNITY-20261008-014.json"))
data["released_in"] = {"task_id": "UNITY-20261008-011", "record_sha256": digest,
                       "change_commits": ["1fc54e15eedd51e04e26cac549d29487dd650008"]}
data.pop("release_gate", None)
_lines, _header, rows = taskctl.read_board(taskctl.board_path())
record, other = taskctl.released_in_record(data, "UNITY-20261008-014", rows, records)
print("released_in_record: ok, releasing task", other, "state", rows[other][1][4], "record sha256", digest[:16])
gate = json.load(open(repo / record["gate_file"]))
print("gate", record["gate_file"], "sha256 equal:", taskctl.sha256(repo / record["gate_file"]) == record["gate_sha256"],
      "verification_result", gate.get("verification_result"))
taskctl.check_released_commits(data, record, gate, records)
print("check_released_commits: ok (1fc54e1 in", record["source_commit"][:12], "and in no earlier hud publication)")
for bad in ("b0c2444561557bb91d4b045bac73f1b6b5f0f6f4",):
    data["released_in"]["change_commits"] = [bad]
    try:
        taskctl.check_released_commits(data, record, gate, records)
        print("UNEXPECTED: accepted", bad)
    except ValueError as exc:
        print("refused as expected:", exc)
