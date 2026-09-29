#!/usr/bin/env python3
"""repro_old.py - run the snapshot-expectation block of the unmodified
publish_aptly.py (taken verbatim from origin/main by its first and last line,
not retyped) on the contract fixtures and print what it decides."""
import hashlib, re, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts' / 'tests'))
import publish_fixtures as fixtures
src = subprocess.run(["git", "show", "origin/main:scripts/publish_aptly.py"], capture_output=True, text=True, check=True).stdout
start = src.index("    source_ok = binary_ok = False\n")
end_marker = '    if not source_ok or not binary_ok: return fail("manifest must include the matching source and binary artifacts")\n'
end = src.index(end_marker) + len(end_marker)
body = "def old_block(artifacts, manifest_path, package, version):\n" + src[start:end] + "    return expected_snapshot_names\n"
ns = {"sha256": lambda p: hashlib.sha256(p.read_bytes()).hexdigest(), "fail": lambda m: "ERROR: " + m}
exec(body, ns)
with tempfile.TemporaryDirectory() as t:
    d = Path(t)
    for name, cd, artifacts, expect in fixtures.cases(d):
        got = ns["old_block"](artifacts, cd / "m.json", fixtures.SRC, fixtures.VER)
        ok = (isinstance(expect, list) and got == expect) or (isinstance(expect, str) and isinstance(got, str) and expect.split(": ", 1)[1] in got)
        print(f"{'OK  ' if ok else 'BAD '} {name}: old -> {got}; contract -> {expect}")
