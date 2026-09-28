#!/usr/bin/env python3
"""UNITY-20260928-005 (agent A): open (not BACKLOG, not closed) tasks on the
board with the package_change / task_kind of their evidence file."""
import json, re
from pathlib import Path
board = Path.home() / "coordinator/TASKS.md"
closed = False
for line in board.read_text().splitlines():
    if line.startswith("## Closed tasks"):
        closed = True
    m = re.match(r"\| (UNITY-\d{8}-\d{3}) \|", line)
    if not m or closed:
        continue
    cols = [c.strip() for c in line.strip().strip("|").split("|")]
    if cols[4] == "BACKLOG":
        continue
    p = Path.home() / "coordinator/evidence" / f"{m.group(1)}.json"
    d = json.loads(p.read_text()) if p.exists() else {}
    print(f"{m.group(1)} {cols[4]:15} owner={cols[2]} package_change={d.get('package_change', '-')} task_kind={d.get('task_kind', '-')}")
