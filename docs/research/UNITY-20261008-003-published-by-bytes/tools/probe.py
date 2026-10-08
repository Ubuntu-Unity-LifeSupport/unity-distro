"""UNITY-20261008-003 probe: for the three past published_by closures, compare
the task's own build with the published build reached through the publish
record (gate_file + gate_sha256 -> build_manifest file + sha256): (1) bytes of
every source/binary equal, else (2) the buildinfo_identical identity.
Usage: probe.py <repo root (main)>"""
import hashlib, json, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "scripts"))
import tested_build as tb
from build_dependencies import installed_build_depends

ONDISK = [Path(x) for x in sys.argv[2:]]  # optional: candidate .buildinfo copies on disk
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

for task in ("UNITY-20260927-052", "UNITY-20260928-020", "UNITY-20261002-011"):
    ev = json.load(open(f"/home/claude/coordinator/evidence/{task}.json"))
    pb = ev["published_by"]["task_id"]
    rec = json.load(open(f"/home/claude/coordinator/publish-records/{pb}.json"))
    gate_path = root / rec["gate_file"]
    gate_ok = sha(gate_path) == rec["gate_sha256"]
    gate = json.load(open(gate_path))
    pub_m_path = root / gate["build_manifest"]["file"]
    pub_ok = sha(pub_m_path) == gate["build_manifest"]["sha256"]
    pub = json.load(open(pub_m_path))
    own_path = root / ev["build_manifest"].split(" ")[0]
    own = json.load(open(own_path))
    sel = lambda m: {a["file"]: a["sha256"] for a in m["artifacts"] if a.get("kind") in ("source", "binary")}
    recd = sel(rec)
    bytes_equal = sel(own) == recd
    print(f"== {task} by {pb}: gate sha ok {gate_ok}, published manifest sha ok {pub_ok}, "
          f"record artifacts = published manifest {sel(pub) == recd}")
    print(f"   (1) bytes equal: {bytes_equal}")
    if bytes_equal:
        print("   VERDICT: PASS by bytes"); continue
    reasons = []
    for label, a, b in (("source_commit", own.get("source_commit"), pub.get("source_commit")),
                        ("source_tree_hash", own.get("source_tree_hash"), pub.get("source_tree_hash")),
                        ("build_dependencies", tb.dependency_identity(own), tb.dependency_identity(pub))):
        if a != b: reasons.append(label)
    def bi(m, mp):
        b = [a for a in m["artifacts"] if a.get("kind") == "buildinfo"]
        if len(b) != 1: return None, f"{len(b)} buildinfo"
        p = mp.parent / b[0]["file"]
        if not p.is_file() and ONDISK:  # not committed (*.buildinfo is ignored): a copy on disk with the manifest's sha256
            hits = [c for c in ONDISK if c.name == b[0]["file"] and sha(c) == b[0]["sha256"]]
            if hits:
                p = hits[0]
                print(f"   on-disk copy for {mp.parent.name}: {p}")
        if not p.is_file(): return None, f"{b[0]['file']} missing"
        if sha(p) != b[0]["sha256"]: return None, f"{b[0]['file']} sha differs"
        return p.read_text(errors="replace"), None
    ot, oe = bi(own, own_path); pt, pe = bi(pub, pub_m_path)
    if oe or pe: reasons.append(f"buildinfo: own {oe} / published {pe}")
    else:
        of, pf = tb.buildinfo_fields(ot), tb.buildinfo_fields(pt)
        reasons += [f"field {k}" for k in tb.BUILDINFO_FIELDS if of.get(k) != pf.get(k)]
        if installed_build_depends(ot) != installed_build_depends(pt): reasons.append("Installed-Build-Depends")
    print(f"   (2) buildinfo_identical: {'yes' if not reasons else 'NO: ' + ', '.join(reasons)}")
    print("   VERDICT:", "PASS by buildinfo_identical" if not reasons else "FAIL")
