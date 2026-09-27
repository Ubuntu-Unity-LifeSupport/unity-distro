#!/usr/bin/env python3
"""Regression tests for scripts/build_sbuild.py (UNITY-20260927-045).

A stub `sbuild` on PATH stands in for the real one: it writes a .dsc, real
.deb/.ddeb files built with dpkg-deb, a .buildinfo and a .changes naming them
next to the source tree, writes its full log to a .build file, and prints that
log to stdout only with --verbose - as sbuild does when stdout is not a
terminal. Run: python3 -m unittest discover -s scripts/tests
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "build_sbuild.py"

STUB = r'''#!/usr/bin/env python3
import hashlib, json, os, subprocess, sys
from pathlib import Path
spec = json.loads(os.environ["STUB_SPEC"])
verbose = "--verbose" in sys.argv[1:]
src, ver = spec["source"], spec["version"]
noepoch = ver.split(":", 1)[-1]
out = Path.cwd().parent
# dpkg-source runs before sbuild's log is set up and always reaches stdout.
print(f"dpkg-source: info: building {src} in ../{src}_{noepoch}.dsc", flush=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_files = []
for name in spec.get("source_files", []):
    path = out / name
    path.write_bytes(os.urandom(64))
    source_files.append(path)
dsc = out / f"{src}_{noepoch}.dsc"
dsc_lines = [f"Format: 3.0 (quilt)", f"Source: {src}", f"Version: {ver}", "Checksums-Sha256:"]
dsc_lines += [f" {sha(p)} {p.stat().st_size} {p.name}" for p in source_files]
dsc_lines += ["Files:"] + [f" {hashlib.md5(p.read_bytes()).hexdigest()} {p.stat().st_size} {p.name}" for p in source_files]
dsc.write_text("\n".join(dsc_lines) + "\n")
log = [f"sbuild (stub) {src} {ver}"] + [f"log line {i}" for i in range(spec.get("log_lines", 50))]
files = []
for name, arch in spec["binaries"]:
    kind = "ddeb" if name.endswith("-dbgsym") else "deb"
    root = out / f".stub-{name}"
    (root / "DEBIAN").mkdir(parents=True, exist_ok=True)
    (root / "DEBIAN" / "control").write_text(
        f"Package: {name}\nVersion: {ver}\nArchitecture: {arch}\n"
        f"Maintainer: test <t@example.com>\nDescription: test\n")
    path = out / f"{name}_{noepoch}_{arch}.{kind}"
    subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(path)],
                   check=True, capture_output=True)
    files.append(path)
buildinfo = out / f"{src}_{noepoch}_amd64.buildinfo"
buildinfo.write_text(f"Source: {src}\nVersion: {ver}\n")
files.append(buildinfo)
for extra in spec.get("unrelated", []):
    (out / extra).write_text("not from this build\n")
if spec.get("source_full"):
    files = [dsc] + source_files + files
lines = [f"Format: 1.8", f"Source: {src}", f"Version: {ver}", "Checksums-Sha256:"]
lines += [f" {sha(p)} {p.stat().st_size} {p.name}" for p in files]
lines += ["Files:"] + [f" {hashlib.md5(p.read_bytes()).hexdigest()} {p.stat().st_size} misc optional {p.name}" for p in files]
(out / f"{src}_{noepoch}_amd64.changes").write_text("\n".join(lines) + "\n")
(out / f"{src}_{noepoch}_amd64.build").write_text("\n".join(log) + "\n")
if verbose:
    print("\n".join(log), flush=True)
'''


class BuildSbuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        bindir = self.base / "bin"
        bindir.mkdir()
        (bindir / "sbuild").write_text(STUB)
        (bindir / "sbuild").chmod(0o755)
        self.env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, source, version, binaries, unrelated=(), source_files=(), source_full=False):
        work = self.base / "work"
        repo = work / source
        (repo / "debian").mkdir(parents=True)
        (repo / "debian" / "changelog").write_text(textwrap.dedent(f"""\
            {source} ({version}) resolute; urgency=medium

              * test

             -- test <t@example.com>  Sun, 27 Sep 2026 00:00:00 +0000
            """))
        git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "test"], check=True)
        spec = {"source": source, "version": version, "binaries": binaries,
                "unrelated": list(unrelated), "log_lines": 50,
                "source_files": list(source_files), "source_full": source_full}
        env = dict(self.env, STUB_SPEC=json.dumps(spec))
        output = self.base / "out"
        result = subprocess.run([sys.executable, str(SCRIPT), "--task-id", "UNITY-20260927-045",
                                 "--source-repo", str(repo), "--target-series", "resolute",
                                 "--output-dir", str(output)],
                                env=env, capture_output=True, text=True)
        manifest = None
        found = list(output.glob("*-build-manifest.json")) if output.exists() else []
        if found:
            manifest = json.loads(found[0].read_text())
        return result, manifest, work, output

    def changes_names(self, work, source, version):
        noepoch = version.split(":", 1)[-1]
        text = (work / f"{source}_{noepoch}_amd64.changes").read_text()
        block = text.split("Checksums-Sha256:\n", 1)[1].split("Files:", 1)[0]
        return {line.split()[2] for line in block.splitlines() if line.strip()}

    def check_complete(self, result, manifest, work, output, source, version):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNotNone(manifest)
        names = {a["file"] for a in manifest["artifacts"]}
        noepoch = version.split(":", 1)[-1]
        self.assertIn(f"{source}_{noepoch}.dsc", names)
        for name in self.changes_names(work, source, version):
            self.assertIn(name, names, f"{name} from .changes missing in manifest")
        for artifact in manifest["artifacts"]:
            path = output / artifact["file"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])
        return names

    def test_plain_version(self):
        """Control: no epoch, binaries named after the source."""
        r, m, w, o = self.build("overlay-scrollbar", "0.2.17.1+16.04.20151117-0ubuntu5+unity1",
                                [["overlay-scrollbar", "all"], ["overlay-scrollbar-gtk2", "amd64"]])
        self.check_complete(r, m, w, o, "overlay-scrollbar", "0.2.17.1+16.04.20151117-0ubuntu5+unity1")

    def test_epoch(self):
        """(1) An epoch in the version never appears in file names."""
        r, m, w, o = self.build("calamares-settings-ubuntu", "1:26.04.12+unity2",
                                [["calamares-settings-ubuntu-unity", "all"],
                                 ["calamares-settings-ubuntu-common", "amd64"]])
        self.check_complete(r, m, w, o, "calamares-settings-ubuntu", "1:26.04.12+unity2")

    def test_binaries_not_named_after_source(self):
        """(2) Binaries come from .changes, including .ddeb, whatever their names."""
        r, m, w, o = self.build("ubuntu-unity-meta", "0.29+unity1",
                                [["ubuntu-unity-desktop", "amd64"], ["ubuntu-unity-desktop-dbgsym", "amd64"]])
        names = self.check_complete(r, m, w, o, "ubuntu-unity-meta", "0.29+unity1")
        self.assertIn("ubuntu-unity-desktop-dbgsym_0.29+unity1_amd64.ddeb", names)

    def test_partially_renamed_binaries_not_dropped(self):
        """(2) xorg-server: one binary contains the source name, one does not."""
        r, m, w, o = self.build("xorg-server", "21.1.22-1ubuntu1.3+unity2",
                                [["xorg-server-source", "all"], ["xserver-xorg-core", "amd64"]])
        names = self.check_complete(r, m, w, o, "xorg-server", "21.1.22-1ubuntu1.3+unity2")
        self.assertIn("xserver-xorg-core_21.1.22-1ubuntu1.3+unity2_amd64.deb", names)

    def test_unrelated_files_ignored(self):
        """Files next to the source that this build's .changes does not name stay out."""
        r, m, w, o = self.build("ubuntu-unity-meta", "0.29+unity1", [["ubuntu-unity-desktop", "amd64"]],
                                unrelated=["ubuntu-unity-desktop_0.28_amd64.deb"])
        names = self.check_complete(r, m, w, o, "ubuntu-unity-meta", "0.29+unity1")
        self.assertNotIn("ubuntu-unity-desktop_0.28_amd64.deb", names)

    def dsc_files(self, work, source, version):
        text = (work / f"{source}_{version.split(':', 1)[-1]}.dsc").read_text()
        block = text.split("Checksums-Sha256:\n", 1)[1].split("Files:", 1)[0]
        return {line.split()[2]: line.split()[0] for line in block.splitlines() if line.strip()}

    def test_source_files_recorded(self):
        """UNITY-20260927-051: every file the .dsc names is in the manifest with the .dsc's sha256."""
        layouts = {"native": ["demo_1.0+unity1.tar.xz"],
                   "3.0 quilt": ["demo_1.0.orig.tar.gz", "demo_1.0-1+unity1.debian.tar.xz"],
                   "1.0": ["demo_1.0.orig.tar.gz", "demo_1.0-1+unity1.diff.gz"]}
        for layout, files in layouts.items():
            with self.subTest(layout=layout):
                self.tearDown(); self.setUp()
                version = "1:1.0+unity1" if layout == "native" else "1:1.0-1+unity1"
                r, m, w, o = self.build("demo", version, [["demo-bin", "amd64"]], source_files=files)
                self.check_complete(r, m, w, o, "demo", version)
                recorded = {a["file"]: a for a in m["artifacts"] if a["kind"] == "source_file"}
                expected = self.dsc_files(w, "demo", version)
                self.assertEqual({f: a["sha256"] for f, a in recorded.items()}, expected)
                for a in recorded.values():
                    self.assertEqual((a["package"], a["version"]), ("demo", version))

    def test_source_full_changes(self):
        """A .changes that also lists the source: no duplicate .dsc, no unknown kinds."""
        r, m, w, o = self.build("demo", "1:1.0-1+unity1", [["demo-bin", "amd64"]],
                                source_files=["demo_1.0.orig.tar.gz", "demo_1.0-1+unity1.debian.tar.xz"],
                                source_full=True)
        self.check_complete(r, m, w, o, "demo", "1:1.0-1+unity1")
        names = [a["file"] for a in m["artifacts"]]
        self.assertEqual(len(names), len(set(names)), names)
        self.assertEqual({a["kind"] for a in m["artifacts"]},
                         {"source", "source_file", "binary", "buildinfo", "changes"})

    def test_full_log(self):
        """(3) The manifest's log is the whole sbuild output, command header first."""
        r, m, w, o = self.build("overlay-scrollbar", "0.2.17.1+16.04.20151117-0ubuntu5+unity1",
                                [["overlay-scrollbar", "all"]])
        self.assertEqual(r.returncode, 0, r.stderr)
        log = (o / m["log"]["file"]).read_text().splitlines()
        self.assertTrue(log[0].startswith("$ sbuild"), log[:3])
        self.assertIn("log line 49", log)
        self.assertEqual(hashlib.sha256((o / m["log"]["file"]).read_bytes()).hexdigest(), m["log"]["sha256"])


if __name__ == "__main__":
    unittest.main()
