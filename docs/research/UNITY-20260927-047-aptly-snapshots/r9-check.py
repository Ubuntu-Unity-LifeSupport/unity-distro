"""R9 check (UNITY-20260927-047): sha256 of every file under state/public
outside candidate/, saved (before) or compared (after); and what is left of
candidate/. Read-only apart from the list file in the scratchpad."""
import hashlib
import json
import sys
from pathlib import Path

PUB = Path("/var/tmp/" + "aptly-rehearsal") / "state/public"
LIST = Path(__file__).with_name("r047_r9_before.json")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


other = {str(p.relative_to(PUB)): sha(p) for p in sorted(PUB.rglob("*"))
         if p.is_file() and not str(p.relative_to(PUB)).startswith("candidate/")}
cand = sorted(str(p.relative_to(PUB)) for p in (PUB / "candidate").rglob("*")) if (PUB / "candidate").exists() else None
if sys.argv[1] == "before":
    LIST.write_text(json.dumps(other))
    print(f"before: {len(other)} files outside candidate/; candidate entries: {len(cand or [])}")
else:
    before = json.loads(LIST.read_text())
    print(f"after: {len(other)} files outside candidate/, unchanged: {other == before}; "
          f"candidate/ exists: {cand is not None}, entries left: {cand}")
