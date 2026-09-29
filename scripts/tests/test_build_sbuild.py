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

# BUILD_SBUILD lets the same tests run against another copy of the script
# (UNITY-20260928-007 ran them against the pre-fix version to show them fail).
SCRIPT = Path(os.environ.get("BUILD_SBUILD", Path(__file__).resolve().parents[1] / "build_sbuild.py"))

STUB = r'''#!/usr/bin/env python3
import gzip, hashlib, io, json, os, subprocess, sys, tarfile
from pathlib import Path
spec = json.loads(os.environ["STUB_SPEC"])
# Options sbuild would hand to dpkg-source (--dpkg-source-opt=X, repeatable).
dpkg_source_opts = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--dpkg-source-opt=")]
verbose = "--verbose" in sys.argv[1:]
src, ver = spec["source"], spec["version"]
noepoch = ver.split(":", 1)[-1]
out = Path.cwd().parent
# dpkg-source runs before sbuild's log is set up and always reaches stdout.
print(f"dpkg-source: info: building {src} in ../{src}_{noepoch}.dsc", flush=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def write_source_file(path, members):
    # Valid archives, as dpkg-source makes them: a .diff.gz with one '+++'
    # line per member, a tarball with the members; anything else random.
    if path.name.endswith(".diff.gz"):
        text = "".join(f"--- a/{m}\n+++ {m}\t2026-09-28\n@@ -0,0 +1 @@\n+x\n" for m in members)
        path.write_bytes(gzip.compress(text.encode()))
    elif ".tar." in path.name:
        with tarfile.open(path, "w:" + path.name.rsplit(".", 1)[1].replace("xz", "xz")) as t:
            for m in members:
                data = b"x\n"; info = tarfile.TarInfo(m); info.size = len(data)
                t.addfile(info, io.BytesIO(data))
    else:
        path.write_bytes(os.urandom(64))
dsc = out / f"{src}_{noepoch}.dsc"
source_files = []
if spec.get("real_source"):
    # What /usr/bin/sbuild does with a source directory (lines 262-312):
    # dpkg-source --before-build, -b and --after-build with the options, in it.
    for step in (["--before-build"], ["-b"], ["--after-build"]):
        rc = subprocess.run(["dpkg-source"] + step + dpkg_source_opts + ["."], stdout=sys.stdout, stderr=sys.stdout).returncode
        if rc:
            print(f"E: Failed to package source directory ({' '.join(step)})", flush=True)
            sys.exit(1)
else:
    for name in spec.get("source_files", []):
        path = out / name
        default = [f"{src}-1.0/debian/changelog"]
        if spec.get("random_source"):
            path.write_bytes(os.urandom(64))
        else:
            write_source_file(path, spec.get("source_members", {}).get(name, default))
        source_files.append(path)
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

    def build(self, source, version, binaries, unrelated=(), source_files=(), source_full=False,
              source_members=None, random_source=False, real=None):
        """real: None (stub makes the source files) or (format, checkout) to
        build a tiny real package with the real dpkg-source; format is "1.0",
        "1.0 native", "3.0 (quilt)" or "3.0 (native)", checkout "clone" or
        "worktree"."""
        work = self.base / "work"
        upstream = version.split(":", 1)[-1].split("-", 1)[0]
        repo = work / (f"{source}-{upstream}" if real else source)
        (repo / "debian").mkdir(parents=True)
        (repo / "debian" / "changelog").write_text(textwrap.dedent(f"""\
            {source} ({version}) resolute; urgency=medium

              * test

             -- test <t@example.com>  Sun, 27 Sep 2026 00:00:00 +0000
            """))
        if real:
            fmt, checkout = real
            (repo / "debian" / "control").write_text(
                f"Source: {source}\nMaintainer: t <t@example.com>\n\nPackage: {source}\nArchitecture: all\nDescription: t\n")
            if fmt.startswith("3.0"):
                (repo / "debian" / "source").mkdir()
                (repo / "debian" / "source" / "format").write_text(fmt + "\n")
            (repo / "src").mkdir()
            (repo / "src" / "a.c").write_text("int main(void) { return 0; }\n")
            if "native" not in fmt:
                subprocess.run(["tar", "-czf", str(work / f"{source}_{upstream}.orig.tar.gz"),
                                "--exclude=debian", "-C", str(work), repo.name], check=True)
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
        if real and real[1] == "worktree":
            main = self.base / "main-checkout"
            repo.rename(main)
            subprocess.run(git + ["-C", str(main), "init", "-q"], check=True)
            subprocess.run(git + ["-C", str(main), "add", "-A"], check=True)
            subprocess.run(git + ["-C", str(main), "commit", "-q", "-m", "test"], check=True)
            subprocess.run(git + ["-C", str(main), "worktree", "add", "-q", str(repo)], check=True, capture_output=True)
        else:
            subprocess.run(git + ["-C", str(repo), "init", "-q"], check=True)
            subprocess.run(git + ["-C", str(repo), "add", "-A"], check=True)
            subprocess.run(git + ["-C", str(repo), "commit", "-q", "-m", "test"], check=True)
        spec = {"source": source, "version": version, "binaries": binaries,
                "unrelated": list(unrelated), "log_lines": 50,
                "source_files": list(source_files), "source_full": source_full,
                "source_members": source_members or {}, "random_source": random_source,
                "real_source": bool(real)}
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

    # UNITY-20260928-007: the source package never carries VCS metadata.

    def source_members(self, work, manifest):
        """Every path in the non-orig source files the manifest records."""
        import gzip, tarfile
        paths = []
        for art in manifest["artifacts"]:
            name = art["file"]
            if art["kind"] != "source_file" or ".orig." in name:
                continue
            path = work / name
            if name.endswith(".diff.gz"):
                paths += [l[4:].split("\t")[0].strip() for l in gzip.decompress(path.read_bytes()).decode().splitlines()
                          if l.startswith("+++ ")]
            else:
                with tarfile.open(path) as t:
                    paths += t.getnames()
        return paths

    def test_real_dpkg_source_no_vcs_metadata(self):
        """End to end with the real dpkg-source, run the way sbuild runs it: every
        format from a clone and a worktree builds, and no .git is in the source."""
        cases = [("1.0", "clone", "1.0-1+unity1"), ("1.0", "worktree", "1.0-1+unity1"),
                 ("1.0 native", "clone", "1.0+unity1"), ("1.0 native", "worktree", "1.0+unity1"),
                 ("3.0 (quilt)", "clone", "1.0-1+unity1"), ("3.0 (native)", "clone", "1.0+unity1")]
        for fmt, checkout, version in cases:
            with self.subTest(format=fmt, checkout=checkout):
                self.tearDown(); self.setUp()
                r, m, w, o = self.build("tiny", version, [["tiny", "all"]], real=(fmt, checkout))
                self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
                self.assertIsNotNone(m)
                members = self.source_members(w, m)
                self.assertTrue(members, "no source file was inspected")
                self.assertEqual([p for p in members if ".git" in p.split("/")], [])

    def test_vcs_metadata_rejected(self):
        """A produced source file with VCS metadata: no manifest, exit 2."""
        cases = {".git file in a .diff.gz": ("demo_1.0.orig.tar.gz", "demo_1.0-1+unity1.diff.gz",
                                             ["demo-1.0/debian/changelog", "demo-1.0/.git"]),
                 ".git/ directory in a native tarball": (None, "demo_1.0+unity1.tar.xz",
                                                        ["demo-1.0/src/a.c", "demo-1.0/.git/HEAD"]),
                 "nested sub/.git in a debian.tar": ("demo_1.0.orig.tar.gz", "demo_1.0-1+unity1.debian.tar.xz",
                                                     ["debian/control", "debian/sub/.git"]),
                 ".svn in a native tarball": (None, "demo_1.0+unity1.tar.gz",
                                              ["demo-1.0/src/a.c", "demo-1.0/.svn/entries"])}
        for label, (orig, produced, members) in cases.items():
            with self.subTest(case=label):
                self.tearDown(); self.setUp()
                version = "1.0-1+unity1" if orig else "1.0+unity1"
                files = ([orig] if orig else []) + [produced]
                r, m, w, o = self.build("demo", version, [["demo-bin", "amd64"]],
                                        source_files=files, source_members={produced: members})
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIsNone(m)
                self.assertIn("version-control metadata", r.stderr)
                self.assertIn(members[-1], r.stderr)

    def test_orig_tarball_not_inspected(self):
        """Upstream's orig tarball may hold .git/.gitignore: it is not ours, it passes."""
        r, m, w, o = self.build("demo", "1.0-1+unity1", [["demo-bin", "amd64"]],
                                source_files=["demo_1.0.orig.tar.gz", "demo_1.0-1+unity1.diff.gz"],
                                source_members={"demo_1.0.orig.tar.gz": ["demo-1.0/.gitignore", "demo-1.0/.git/config"]})
        self.check_complete(r, m, w, o, "demo", "1.0-1+unity1")

    def test_unreadable_source_file_fails_closed(self):
        """A produced source file that cannot be read is not waved through."""
        r, m, w, o = self.build("demo", "1.0-1+unity1", [["demo-bin", "amd64"]],
                                source_files=["demo_1.0.orig.tar.gz", "demo_1.0-1+unity1.diff.gz"],
                                random_source=True)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIsNone(m)
        self.assertIn("cannot inspect", r.stderr)


if __name__ == "__main__":
    unittest.main()
