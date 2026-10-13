#!/usr/bin/env python3
"""UNITY-20261008-003: run taskctl's covering_record + check_own_build, as the
PUBLISHED transition does, on the three past published_by closures, with
their real evidence and the publisher's write-once records. Read-only.
Usage: past-closures.py <repository root with this branch>"""
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "scripts"))
import taskctl  # noqa: E402

RECORDS = Path.home() / "coordinator/publish-records"
for task in ("UNITY-20260927-052", "UNITY-20260928-020", "UNITY-20261002-011"):
    data = json.loads((Path.home() / f"coordinator/evidence/{task}.json").read_text())
    try:
        record, other = taskctl.covering_record(data, task, RECORDS)
        taskctl.check_own_build(data, task, record, root)
        print(f"{task} through {other}: ACCEPTED")
    except ValueError as exc:
        text = str(exc)
        reason = text.split(": ", 1)[-1] if "buildinfo_identical to the published build" in text else text
        print(f"{task} through {data['published_by']['task_id']}: REFUSED - {reason[:300]}")
