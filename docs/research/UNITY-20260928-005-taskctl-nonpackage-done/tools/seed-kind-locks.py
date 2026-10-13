#!/usr/bin/env python3
"""UNITY-20260928-005 (agent A): at deployment of the task kinds, give every
open task its <id>.kind lock at once, so that no task can be relabelled by an
edit of its evidence before its first transition under the new taskctl.

Kind: --set ID=KIND if given, else what taskctl.resolve_kind() reads from the
task's evidence (package_change=true or package markers -> package). Tasks
whose kind cannot be resolved are listed and get their lock at READY_FOR_FIX.
An existing lock is never changed. Run by the coordinator at merge:

  python3 docs/research/UNITY-20260928-005-taskctl-nonpackage-done/tools/seed-kind-locks.py \\
      --dry-run --set UNITY-20260927-047=operation --set UNITY-20260928-007=tool
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
import taskctl  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--set", action="append", default=[], metavar="ID=KIND")
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()
overrides = dict(item.split("=", 1) for item in args.set)
for kind in overrides.values():
    if kind not in taskctl.KINDS:
        sys.exit(f"unknown kind {kind}")
board = taskctl.board_path()
closed = False
status = 0
for line in board.read_text(encoding="utf-8").splitlines():
    if line.startswith("## Closed tasks"):
        closed = True
    m = re.match(r"\| (UNITY-\d{8}-\d{3,}) \|", line)
    if not m or closed:
        continue
    task_id, state = m.group(1), taskctl.split_row(line)[4]
    if state == "BACKLOG":
        continue
    evidence = board.parent / "evidence" / f"{task_id}.json"
    data = json.loads(evidence.read_text(encoding="utf-8")) if evidence.is_file() else {}
    try:
        resolved = taskctl.resolve_kind(data)
    except ValueError as exc:
        print(f"{task_id} {state}: CONFLICT in evidence: {exc}"); status = 1; continue
    kind = overrides.get(task_id, resolved)
    if resolved is not None and kind != resolved:
        print(f"{task_id} {state}: CONFLICT --set {kind} but evidence resolves to {resolved}"); status = 1; continue
    lock = taskctl.kind_lock_path(task_id)
    try:
        held = taskctl.read_kind_lock(lock)
    except ValueError as exc:
        print(f"{task_id} {state}: CONFLICT invalid lock: {exc}"); status = 1; continue
    if held is not None:
        if kind is not None and held != kind:
            print(f"{task_id} {state}: CONFLICT already held to {held}, evidence or --set says {kind}"); status = 1
        else:
            print(f"{task_id} {state}: already held to {held}")
        continue
    if kind is None:
        print(f"{task_id} {state}: no kind yet - lock at READY_FOR_FIX"); continue
    if not args.dry_run:
        taskctl.write_kind_lock(lock, kind)
    print(f"{task_id} {state}: {'would lock' if args.dry_run else 'locked'} {kind}")
sys.exit(status)
