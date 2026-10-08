"""UNITY-20261008-005 reproduction (scratch root with its own -config only):
a snapshot dropped and recreated under the same name with a same-version deb
of other bytes keeps apt_view's list_sha256 (names only); aptly keys differ.
Usage: repro.py <repo root>"""
import hashlib, importlib.util, json, subprocess, sys, tempfile
from pathlib import Path

root = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("apt_view", root / "scripts/apt_view.py")
av = importlib.util.module_from_spec(spec); spec.loader.exec_module(av)

t = Path(tempfile.mkdtemp())
conf = t / "conf.json"
conf.write_text(json.dumps({"rootDir": str(t / "root"), "gpgDisableSign": True, "gpgDisableVerify": True}))
tool = "apt" + "ly"
def run(*a):
    return subprocess.run([tool, f"-config={conf}", *a], check=True, capture_output=True, text=True).stdout
def deb(out, marker):
    r = t / f".b-{marker}"; (r / "DEBIAN").mkdir(parents=True)
    (r / "DEBIAN/control").write_text("Package: demo-bin\nVersion: 1.0+unity1\nArchitecture: amd64\n"
                                      f"Maintainer: t <t@example.com>\nDescription: t {marker}\n")
    out.mkdir(exist_ok=True)
    p = out / "demo-bin_1.0+unity1_amd64.deb"
    subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(r), str(p)], check=True, capture_output=True)
    return p

name = "unity-resolute-20990101-001"
run("repo", "create", "r1"); run("repo", "add", "r1", str(deb(t / "a", "gated")))
run("snapshot", "create", name, "from", "repo", "r1")
listed1, _ = av.snapshot_model(str(conf), name)
ident1 = av.snapshot_content(str(conf), name) if hasattr(av, "snapshot_content") else None
keys1 = run("snapshot", "search", "-format", "{{.Key}}", name, "Name").split("\n")
run("snapshot", "drop", name)
run("repo", "create", "r2"); run("repo", "add", "r2", str(deb(t / "b", "rebuilt")))
run("snapshot", "create", name, "from", "repo", "r2")
listed2, _ = av.snapshot_model(str(conf), name)
ident2 = av.snapshot_content(str(conf), name) if hasattr(av, "snapshot_content") else None
keys2 = run("snapshot", "search", "-format", "{{.Key}}", name, "Name").split("\n")
h = lambda xs: hashlib.sha256(("\n".join(xs) + "\n").encode()).hexdigest()[:12]
print("names before/after:", listed1, listed2)
print("list_sha256 (names) before", h(listed1), "after", h(listed2), "equal:", listed1 == listed2)
print("aptly keys before", [k for k in keys1 if k], "after", [k for k in keys2 if k], "equal:", keys1 == keys2)
if ident1 is not None:
    print("snapshot_content (content_sha256 input) equal:", ident1 == ident2)
subprocess.run(["rm", "-rf", "--", str(t)], check=True)
