#!/usr/bin/env python3
"""check-manifest.py OUTDIR - compare a build_sbuild.py manifest with the
.changes it names: every file of Checksums-Sha256 must be in the manifest with
the same sha256, and every manifest file must hash to its recorded sha256."""
import hashlib, json, sys
from pathlib import Path
out = Path(sys.argv[1])
m = json.loads(next(out.glob("*-build-manifest.json")).read_text())
arts = {a["file"]: a for a in m["artifacts"]}
changes = [a for a in m["artifacts"] if a["kind"] == "changes"]
ok = len(changes) == 1
listed = {}
if ok:
    sec = None
    for line in (out / changes[0]["file"]).read_text().splitlines():
        if line and not line[0].isspace(): sec = line.split(":", 1)[0]
        elif sec == "Checksums-Sha256" and line.strip():
            d, _, n = line.split(); listed[n] = d
for n, d in listed.items():
    if n not in arts or arts[n]["sha256"] != d: ok = False; print("MISSING/MISMATCH", n)
for n, a in arts.items():
    if hashlib.sha256((out / n).read_bytes()).hexdigest() != a["sha256"]: ok = False; print("BAD HASH", n)
log = out / m["log"]["file"]
print(f"{m['package']} {m['candidate_version']}: changes lists {len(listed)}, manifest {len(arts)} artifacts, "
      f"binaries {sum(a['kind']=='binary' for a in arts.values())}, log {sum(1 for _ in log.open())} lines, "
      f"header first: {log.read_text().startswith('$ sbuild')}, result {'PASS' if ok else 'FAIL'}")
