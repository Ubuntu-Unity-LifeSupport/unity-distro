"""UNITY-20261008-002 reproduction: in a scratch aptly root (its own -config,
never the live repository), a snapshot holding a same-version binary with
other bytes passes the snapshot checks publish_aptly.py runs today: the
<Package>_<Version>_<Arch> name check on `snapshot show -with-packages` and the
source package Checksums-Sha256 check. Usage: repro.py <repo root>"""
import hashlib, importlib.util, json, re, subprocess, sys, tempfile
from pathlib import Path

root = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("publish_aptly", root / "scripts/publish_aptly.py")
pa = importlib.util.module_from_spec(spec); spec.loader.exec_module(pa)

t = Path(tempfile.mkdtemp())
conf = t / "aptly.conf"
conf.write_text(json.dumps({"rootDir": str(t / "aptly"), "gpgDisableSign": True, "gpgDisableVerify": True}))
def aptly(*a, check=True):
    return subprocess.run(["aptly", f"-config={conf}", *a], check=check, capture_output=True, text=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def deb(out, name, version, marker):
    r = t / f".b-{name}-{marker}"; (r / "DEBIAN").mkdir(parents=True)
    (r / "DEBIAN/control").write_text(f"Package: {name}\nVersion: {version}\nArchitecture: amd64\nSource: demo\n"
                                      f"Maintainer: t <t@example.com>\nDescription: t {marker}\n")
    p = out / f"{name}_{version}_amd64.deb"
    subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(r), str(p)], check=True, capture_output=True)
    return p

V = "1.0+unity1"
built, rebuilt = t / "built", t / "rebuilt"
for d in (built, rebuilt): d.mkdir()
src = t / "demo-src"; (src / "debian/source").mkdir(parents=True)
(src / "debian/source/format").write_text("3.0 (native)\n")
(src / "debian/control").write_text("Source: demo\nMaintainer: t <t@example.com>\n\nPackage: demo-bin\nArchitecture: amd64\nDescription: t\n")
(src / "debian/changelog").write_text(f"demo ({V}) resolute; urgency=medium\n\n  * t\n\n -- t <t@example.com>  Tue, 29 Sep 2026 00:00:00 +0000\n")
subprocess.run(["dpkg-source", "-b", str(src)], cwd=built, check=True, capture_output=True)
dsc, tar = sorted(built.glob("demo_*"))
gated = deb(built, "demo-bin", V, "gated")           # what the manifest names
other = deb(rebuilt, "demo-bin", V, "rebuilt")       # same name and version, other bytes
artifacts = [{"file": dsc.name, "kind": "source", "package": "demo", "version": V, "sha256": sha(dsc)},
             {"file": tar.name, "kind": "source_file", "package": "demo", "version": V, "sha256": sha(tar)},
             {"file": gated.name, "kind": "binary", "package": "demo-bin", "version": V, "architecture": "amd64",
              "sha256": sha(gated)}]
print("manifest demo-bin sha256", sha(gated)[:12], "| in repository", sha(other)[:12])
aptly("repo", "create", "r")
aptly("repo", "add", "r", str(dsc), str(other))
aptly("snapshot", "create", "unity-resolute-20990101-001", "from", "repo", "r")
snap = "unity-resolute-20990101-001"

# the checks publish_aptly.py main() runs on the snapshot today (lines 450-458 on main)
shown = aptly("snapshot", "show", "-with-packages", snap).stdout
names = [f"demo_{V}_source", f"demo-bin_{V}_amd64"]
names_ok = all(re.search(rf"(?m)^\s*{re.escape(n)}\s*$", shown) for n in names)
q = aptly("snapshot", "search", "-format", '{{index . "Checksums-Sha256"}}', snap, f"Name (demo), $Architecture (source), Version (= {V})")
source_error = pa.source_package_matches(artifacts, pa.dsc_checksums("Checksums-Sha256:\n" + q.stdout))
print("name check:", "pass" if names_ok else "FAIL", "| source check:", source_error or "pass")
found = aptly("snapshot", "search", "-format", '{{index . "SHA256"}}', snap, f"Name (demo-bin), Version (= {V}), Architecture (amd64)").stdout.split()
print("snapshot demo-bin SHA256 field:", [f[:12] for f in found], "| equals manifest:", found == [sha(gated)])
print("RESULT (checks of main c672ce9):", "ACCEPTED" if names_ok and not source_error else "refused")
if hasattr(pa, "check_gated_snapshot"):  # UNITY-20261008-002
    error = pa.check_gated_snapshot(snap, names, artifacts, run=lambda a: subprocess.run(
        ["aptly", f"-config={conf}", *a], check=False, capture_output=True, text=True))
    print("RESULT (check_gated_snapshot):", f"refused: {error}" if error else "ACCEPTED")
subprocess.run(["rm", "-rf", "--", str(t)], check=True)
