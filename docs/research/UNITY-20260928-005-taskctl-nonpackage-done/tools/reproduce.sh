#!/bin/bash
# UNITY-20260928-005 (agent A): the three gaps of taskctl.py for non-package
# tasks, on a temporary board (TASKCTL_BOARD) with fixture evidence files.
# usage: [WITH_KINDS=1] reproduce.sh [TASKCTL]   (default: scripts/taskctl.py of this checkout)
# WITH_KINDS=1 adds task_kind to the fixtures (tool, operation with its plan
# and authorization, tool) - the evidence the fixed taskctl asks for.
set -u
TC=${1:-$(git rev-parse --show-toplevel)/scripts/taskctl.py}
T=$(mktemp -d); trap 'rm -rf "${T:?}"' EXIT
row() { echo "| $1 | $2 | A | target-desktop | $3 | 2099-01-01 00:00Z | 2099-01-01 08:00Z | 2099-01-01 00:00Z | - |"; }
{ echo "# test board"; echo
  echo "| ID | Title | Owner | Machine | State | Claimed | Lease | Updated | Evidence |"
  echo "|---|---|---|---|---|---|---|---|---|"
  row UNITY-20990101-001 "tool change, Verifier PASS" REVIEW
  row UNITY-20990101-002 "provisioning (create repositories)" INVESTIGATING
  row UNITY-20990101-003 "tool change, no Verifier record" VERIFYING
  echo; echo "## Closed tasks"; echo
  echo "| ID | Title / package | Owner | Machine / resource | State | Claimed (UTC) | Lease until (UTC) | Updated (UTC) | Evidence |"
  echo "|---|---|---|---|---|---|---|---|---|"; } > "$T/board.md"
cat > "$T/e1.json" <<'J'
{"task_id": "UNITY-20990101-001", "package_change": false, "verification_result": "PASS",
 "review_status": "INDEPENDENTLY_REPRODUCED", "verification_record": "x", "terminal_evidence": "merged"}
J
cat > "$T/e2.json" <<'J'
{"task_id": "UNITY-20990101-002", "package_change": false, "implementation_plan": "create repositories",
 "validation_record": "git ls-remote", "terminal_evidence": "done"}
J
cat > "$T/e3.json" <<'J'
{"task_id": "UNITY-20990101-003", "package_change": false, "validation_record": "unit tests", "terminal_evidence": "merged"}
J
if [ -n "${WITH_KINDS:-}" ]; then
  python3 - "$T" <<'P'
import json, sys
from pathlib import Path
t = Path(sys.argv[1])
def add(name, **kv):
    p = t / name; d = json.loads(p.read_text()); d.update(kv); p.write_text(json.dumps(d))
add("e1.json", task_kind="tool")
add("e2.json", task_kind="operation", scope="create repositories", chosen_approach="gh repo create + push",
    correct_layer="our GitHub organisation", existing_state_check="gh repo list: none of them exists",
    architectural_task=False, design_challenger_required=False,
    authorization={"approved_by": "May", "reference": "~/coordinator/PENDING-MAY.md 2099-01-01", "scope": "create repositories"})
add("e3.json", task_kind="tool", regression_test="unit tests")
P
fi
run() {  # ID STATE EVIDENCE
  echo "\$ taskctl transition $1 $2 --evidence $(basename "$3")   [$(grep -oE "$1 \| [^|]+ \| A \| [^|]+ \| [A-Z_]+" "$T/board.md" | awk -F'|' '{print $NF}' | tr -d ' ')]"
  TASKCTL_BOARD="$T/board.md" python3 "$TC" transition "$1" "$2" --actor A --evidence "$3" > "$T/out" 2>&1
  echo "  rc=$? $(grep -oE 'taskctl: .*' "$T/out" || echo "state now: $(grep -oE "$1 \| [^|]+ \| A \| [^|]+ \| [A-Z_]+" "$T/board.md" | awk -F'|' '{print $NF}' | tr -d ' ')")"
}
echo "## taskctl: $TC ($(git -C "$(dirname "$TC")" rev-parse --short HEAD 2>/dev/null))"
echo "## fixtures:"; for f in "$T"/e*.json; do echo "  $(basename "$f"): $(tr -d '\n' < "$f")"; done
run UNITY-20990101-001 DONE "$T/e1.json"
run UNITY-20990101-002 IMPLEMENTING "$T/e2.json"
run UNITY-20990101-002 READY_FOR_FIX "$T/e2.json"
run UNITY-20990101-002 IMPLEMENTING "$T/e2.json"
run UNITY-20990101-002 VERIFYING "$T/e2.json"
run UNITY-20990101-002 DONE "$T/e2.json"
run UNITY-20990101-003 DONE "$T/e3.json"
