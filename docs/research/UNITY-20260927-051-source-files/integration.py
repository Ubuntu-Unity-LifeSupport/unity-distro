#!/usr/bin/env python3
"""integration.py OUT SRCTREE SCRATCH - with a real build_sbuild.py manifest
(OUT): (A) put its own .dsc, source files and binaries into a scratch aptly
(own rootDir), snapshot, and run the publisher's snapshot_expectations(),
source query and source_package_matches(); (B) the same with a source
regenerated from SRCTREE with one file changed - same name and version,
other content - which must be refused."""
import importlib.util, json, shutil, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location("pa", here.parents[3] / "scripts" / "publish_aptly.py")
pa = importlib.util.module_from_spec(spec); spec.loader.exec_module(pa)
out, srctree, scratch = map(Path, sys.argv[1:4])
m = json.loads(next(out.glob("*-build-manifest.json")).read_text())
names, err = pa.snapshot_expectations(m["artifacts"], out, m["package"], m["candidate_version"])
print(f"snapshot_expectations: {err or names}")

def snapshot(label, files):
    d = scratch / label
    if d.exists(): shutil.rmtree(d)
    (d / "in").mkdir(parents=True)
    conf = d / "aptly.conf"
    conf.write_text(json.dumps({"rootDir": str(d / "root"), "gpgDisableSign": True, "gpgDisableVerify": True}))
    for f in files: shutil.copy(f, d / "in")
    a = ["aptly", f"-config={conf}"]
    for args in (["repo", "create", "r"], ["repo", "add", "r", str(d / "in")], ["snapshot", "create", "s", "from", "repo", "r"]):
        subprocess.run(a + args, check=True, capture_output=True)
    q = subprocess.run(a + ["snapshot", "search", "-format", '{{index . "Checksums-Sha256"}}', "s",
                            f"Name ({m['package']}), $Architecture (source), Version (= {m['candidate_version']})"],
                       check=True, capture_output=True, text=True).stdout
    return pa.dsc_checksums("Checksums-Sha256:\n" + q)

binaries = [out / a["file"] for a in m["artifacts"] if a["kind"] == "binary"]
own = [out / a["file"] for a in m["artifacts"] if a["kind"] in ("source", "source_file")]
got = snapshot("A-built-source", own + binaries)
print(f"A (built source): snapshot source files {sorted(got)} -> {pa.source_package_matches(m['artifacts'], got) or 'MATCH'}")
regen = scratch / "regen"
if regen.exists(): shutil.rmtree(regen)
tree = regen / srctree.name
shutil.copytree(srctree, tree, ignore=shutil.ignore_patterns(".git"))
readme = next(tree / n for n in ("README.md", "README", "Makefile") if (tree / n).is_file())
readme.write_text(readme.read_text() + "\nregenerated\n")
subprocess.run(["dpkg-source", "-b", tree.name], cwd=regen, check=True, capture_output=True)
other = sorted(p for p in regen.iterdir() if p.is_file())
got = snapshot("B-regenerated-source", other + binaries)
print(f"B (regenerated source, same version, {readme.name} changed): -> {pa.source_package_matches(m['artifacts'], got) or 'MATCH'}")
