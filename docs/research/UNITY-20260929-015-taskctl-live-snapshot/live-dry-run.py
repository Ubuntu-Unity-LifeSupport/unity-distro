#!/usr/bin/env python3
"""UNITY-20260929-015 validation: confirm_live_publication on the real
UNITY-20260927-021 publish record against the real live aptly database.

Nothing is published and `publish show` is not run: its answer is taken from
the later publication's own write-once record (UNITY-20260928-019, the switch
that replaced -021-r2). Every other call is a real read-only
`snapshot search` through taskctl's own runner.
Usage: live-dry-run.py <scripts dir>
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, sys.argv[1])
import taskctl  # noqa: E402

records = Path.home() / "coordinator/publish-records"
rec = json.loads((records / "UNITY-20260927-021.json").read_text())
later = json.loads((records / "UNITY-20260928-019.json").read_text())


class Shown:
    returncode, stderr = 0, ""

    def __init__(self, name):
        self.stdout = f"Prefix: .\nDistribution: resolute\nSources:\n  main: {name} [snapshot]\n"


def run(args):
    if args[:2] == ["publish", "show"]:
        print(f"(publish show answered from {later['task_id']} record: {later['snapshot']})")
        return Shown(later["snapshot"])
    assert args[:2] == ["snapshot", "search"], args
    result = taskctl.run_aptly_read(args)
    print(f"snapshot search {args[4]} {args[5]!r} -> rc {result.returncode}, {len(result.stdout.splitlines())} line(s)")
    return result


print(f"record {rec['task_id']}: snapshot {rec['snapshot']}, published_at {rec['published_at']}, "
      f"post_publish_check {rec['post_publish_check']}, {len(rec['artifacts'])} artifacts")
print("result:", taskctl.confirm_live_publication(rec, rec["distribution"], rec["prefix"], run=run) or "CONFIRMED")

# the same record with one binary hash altered must be refused
bad = json.loads(json.dumps(rec))
next(a for a in bad["artifacts"] if a["kind"] == "binary")["sha256"] = "0" * 64
print("altered binary hash:", taskctl.confirm_live_publication(bad, rec["distribution"], rec["prefix"], run=run))
