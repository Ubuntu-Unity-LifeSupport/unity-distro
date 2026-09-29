#!/usr/bin/env python3
"""integration.py OUTDIR SRCDIR SCRATCH - put the real files of a
build_sbuild.py manifest (binaries from OUTDIR, the source package from
SRCDIR) into a scratch aptly (own rootDir under SCRATCH, not /srv/aptly), make
a snapshot, and check every entry snapshot_expectations() requires against
`aptly snapshot show -with-packages` with the publisher's own pattern."""
import importlib.util, json, re, shutil, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location("publish_aptly", here.parents[3] / "scripts" / "publish_aptly.py")
pa = importlib.util.module_from_spec(spec); spec.loader.exec_module(pa)
out, srcdir, scratch = map(Path, sys.argv[1:4])
m = json.loads(next(out.glob("*-build-manifest.json")).read_text())
names, err = pa.snapshot_expectations(m["artifacts"], out, m["package"], m["candidate_version"])
print(f"{m['package']} {m['candidate_version']}: expectations {'ERROR ' + err if err else names}")
if err: sys.exit(1)
if scratch.exists(): shutil.rmtree(scratch)
(scratch / "in").mkdir(parents=True)
conf = scratch / "aptly.conf"
conf.write_text(json.dumps({"rootDir": str(scratch / "root"), "gpgDisableSign": True, "gpgDisableVerify": True}))
for a in m["artifacts"]:
    if a["kind"] == "binary": shutil.copy(out / a["file"], scratch / "in")
dsc = next(a["file"] for a in m["artifacts"] if a["kind"] == "source")
section = None
for line in (srcdir / dsc).read_text().splitlines():
    if line and not line[0].isspace(): section = line.split(":", 1)[0]
    elif section == "Files" and line.strip(): shutil.copy(srcdir / line.split()[-1], scratch / "in")
shutil.copy(srcdir / dsc, scratch / "in")
A = ["aptly", f"-config={conf}"]
for args in (["repo", "create", "t"], ["repo", "add", "t", str(scratch / "in")], ["snapshot", "create", "s", "from", "repo", "t"]):
    subprocess.run(A + args, check=True, capture_output=True)
shown = subprocess.run(A + ["snapshot", "show", "-with-packages", "s"], check=True, capture_output=True, text=True).stdout
missing = [n for n in names if not re.search(rf"(?m)^\s*{re.escape(n)}\s*$", shown)]
print(f"snapshot entries: {len(re.findall(r'(?m)^  \S+_\S+_\S+$', shown))}; missing expected: {missing or 'none'}; result {'PASS' if not missing else 'FAIL'}")
