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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chroot_fixtures import make_chroot  # noqa: E402

# BUILD_SBUILD lets the same tests run against another copy of the script
# (UNITY-20260928-007 ran them against the pre-fix version to show them fail).
SCRIPT = Path(os.environ.get("BUILD_SBUILD", Path(__file__).resolve().parents[1] / "build_sbuild.py"))
SBUILD_CONFIG = SCRIPT.resolve().parents[1] / "build" / "sbuild-config.pl"

STUB = r'''#!/usr/bin/env python3
import gzip, hashlib, io, json, os, subprocess, sys, tarfile
from pathlib import Path
spec = json.loads(os.environ["STUB_SPEC"])
# Options sbuild would hand to dpkg-source (--dpkg-source-opt=X, repeatable).
dpkg_source_opts = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--dpkg-source-opt=")]
verbose = "--verbose" in sys.argv[1:]
# UNITY-20260929-013: record the argv; optionally change an extra package
# during the "build".
if spec.get("argv_file"):
    Path(spec["argv_file"]).write_text(json.dumps(sys.argv[1:]))
extras = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--extra-package=")]
# UNITY-20260929-016: the chroot sbuild is given; what sbuild logs about it.
chroot = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--chroot=")), None)
if spec.get("env_file"):
    Path(spec["env_file"]).write_text(json.dumps({"SBUILD_CONFIG": os.environ.get("SBUILD_CONFIG")}))
if spec.get("tamper_chroot") and chroot:
    with open(chroot, "ab") as f:
        f.write(b"tampered")
stamp = Path(chroot).name.rsplit("-", 1)[-1][:-len(".tar.zst")] if chroot else ""
chroot_log = [] if spec.get("no_unpack") else [f"I: Unpacking {chroot} to /var/tmp/sbuild-claude/sbuild-unshare-AbCdEf..."]
chroot_log += [f"Get:5 https://snapshot.ubuntu.com/ubuntu/{stamp} resolute InRelease [136 kB]",
               "Unpacking mount (2.41-4ubuntu4) ...", "0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded."]
chroot_log += spec.get("log_extra", [])
if spec.get("tamper") and extras:
    with open(extras[0], "ab") as f:
        f.write(b"tampered")
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
log = [f"sbuild (stub) {src} {ver}"] + chroot_log + [f"log line {i}" for i in range(spec.get("log_lines", 50))]
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
text = f"Source: {src}\nVersion: {ver}\n"
if spec.get("installed") is not None:
    # as dpkg-genbuildinfo writes it: one entry per line, comma-separated
    entries = spec["installed"]
    text += "Installed-Build-Depends:\n" + ",\n".join(f" {e}" for e in entries) + "\n"
    text += "Environment:\n DEB_BUILD_OPTIONS=\"parallel=4\"\n"
buildinfo.write_text(text)
if not spec.get("no_buildinfo"):
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
        self.chroot = make_chroot(self.base / "chroots")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, source, version, binaries, unrelated=(), source_files=(), source_full=False,
              source_members=None, random_source=False, real=None, extra=(), installed=None,
              tamper=False, no_buildinfo=False, pool_root=None, cwd=None, chroot=None, chroot_args=(),
              log_extra=(), no_unpack=False, tamper_chroot=False):
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
                "real_source": bool(real), "argv_file": str(self.base / "sbuild-argv.json"),
                "installed": installed, "tamper": tamper, "no_buildinfo": no_buildinfo,
                "env_file": str(self.base / "sbuild-env.json"), "log_extra": list(log_extra),
                "no_unpack": no_unpack, "tamper_chroot": tamper_chroot}
        env = dict(self.env, STUB_SPEC=json.dumps(spec))
        env["BUILD_SBUILD_POOL_ROOT"] = str(pool_root or self.base / "no-pool")
        output = self.base / "out"
        command = [sys.executable, str(SCRIPT), "--task-id", "UNITY-20260927-045",
                   "--source-repo", str(repo), "--target-series", "resolute", "--output-dir", str(output)]
        if chroot is not False:
            command += ["--chroot-tarball", str(chroot or self.chroot)]
        command += list(chroot_args)
        for path in extra:
            command += ["--extra-package", str(path)]
        result = subprocess.run(command, env=env, capture_output=True, text=True, cwd=cwd)
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
        self.assertTrue(log[0].startswith(f"$ SBUILD_CONFIG={SBUILD_CONFIG} sbuild "), log[:3])  # -016
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

    # UNITY-20260929-013: --extra-package, recorded in build_dependencies.

    BASE_COMMAND = ["sbuild", "-d", "resolute", "--no-clean-source", "--verbose",
                    "--dpkg-source-opt=-i", "--dpkg-source-opt=-I"]
    BASE_KEYS = {"schema", "task_id", "package", "candidate_version", "target_series", "source_repo",
                 "source_commit", "source_tree_hash", "build_command", "build_started", "build_finished",
                 "result", "log", "artifacts"}

    def base_command(self, chroot=None):
        """UNITY-20260929-016: the command now names the chroot."""
        return self.BASE_COMMAND + ["--chroot-mode=unshare", f"--chroot={(chroot or self.chroot).resolve()}"]

    def test_chroot_recorded_and_config_passed(self):
        """UNITY-20260929-016: the manifest records the tarball; sbuild gets SBUILD_CONFIG."""
        r, m, w, o = self.build("demo", "1.0+unity1", [["demo", "amd64"]])
        self.assertEqual(r.returncode, 0, r.stderr)
        c = m["chroot"]
        self.assertEqual(c["tarball"], str(self.chroot.resolve()))
        self.assertEqual(c["sha256"], hashlib.sha256(self.chroot.read_bytes()).hexdigest())
        self.assertEqual(len(c["sources"]), 3)
        self.assertTrue(all(f"snapshot.ubuntu.com/ubuntu/{c['snapshot']} " in line for line in c["sources"]))
        self.assertEqual(len(c["log_inrelease"]), 1)
        self.assertFalse(c["allow_old_chroot"])
        env = json.loads((self.base / "sbuild-env.json").read_text())
        self.assertEqual(env["SBUILD_CONFIG"], str(SBUILD_CONFIG))
        self.assertIn("$unshare_mmdebstrap_auto_create = 0;", SBUILD_CONFIG.read_text())

    def test_chroot_refused_before_sbuild(self):
        """A bad tarball is refused before sbuild runs, and nothing is written."""
        d = self.base / "bad"
        cases = {
            "missing": lambda: d / "resolute-amd64-20260929T000000Z.tar.zst",
            "no sidecar": lambda: make_chroot(d, write_sidecar=False),
            "live mirror": lambda: make_chroot(d, lines=["deb http://de.archive.ubuntu.com/ubuntu resolute main universe restricted"]),
            "old": lambda: make_chroot(d, stamp="20260901T000000Z"),
            "symlink": lambda: self.symlink_to(make_chroot(d)),
        }
        for label, make in cases.items():
            with self.subTest(case=label):
                self.tearDown(); self.setUp()
                r, m, w, o = self.build("demo", "1.0+unity1", [["demo", "amd64"]], chroot=make())
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIsNone(m)
                self.assertIsNone(self.sbuild_argv(), f"sbuild ran for: {label}")
                self.assertEqual(sorted(q.name for q in o.iterdir()) if o.exists() else [], [])
                self.assertIn("chroot tarball", r.stderr)  # this refusal, not an argument error

    def symlink_to(self, target):
        link = self.base / "current.tar.zst"
        link.symlink_to(target)
        return link

    def test_old_chroot_allowed_and_recorded(self):
        old = make_chroot(self.base / "old", stamp="20260901T000000Z")
        r, m, w, o = self.build("demo", "1.0+unity1", [["demo", "amd64"]], chroot=old, chroot_args=["--allow-old-chroot"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(m["chroot"]["allow_old_chroot"])
        self.assertTrue(m["chroot"]["older_than_max_age"])

    def test_chroot_log_refusals(self):
        """After sbuild: on-demand chroot, tarball not unpacked, foreign fetch,
        tarball changed - refused, no manifest."""
        cases = {
            "on-demand": {"log_extra": ["I: Creating chroot on-demand by running:"]},
            "not unpacked": {"no_unpack": True},
            "foreign mirror": {"log_extra": ["Hit:7 http://de.archive.ubuntu.com/ubuntu resolute InRelease"]},
            "tarball changed": {"tamper_chroot": True},
        }
        for label, kwargs in cases.items():
            with self.subTest(case=label):
                self.tearDown(); self.setUp()
                r, m, w, o = self.build("demo", "1.0+unity1", [["demo", "amd64"]], **kwargs)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIsNone(m)
                self.assertIn("no manifest written", r.stderr)
                self.assertTrue("chroot" in r.stderr or "outside the snapshot" in r.stderr, r.stderr)

    def test_tested_with(self):
        """--tested-with: the tested build's chroot must be this one."""
        r, m, w, o = self.build("demo", "1.0+unity1", [["demo", "amd64"]])
        self.assertEqual(r.returncode, 0, r.stderr)
        tested = self.base / "tested-manifest.json"
        tested.write_text(json.dumps(m))
        for p in (self.base / "work", self.base / "out"):
            subprocess.run(["rm", "-rf", "--", str(p)], check=True)
        (self.base / "sbuild-argv.json").unlink()
        r2, m2, w2, o2 = self.build("demo", "1.0+unity1", [["demo", "amd64"]], chroot_args=["--tested-with", str(tested)])
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(m2["chroot"]["tested_with"]["chroot_sha256"], m["chroot"]["sha256"])
        other = make_chroot(self.base / "other")
        for p in (self.base / "work", self.base / "out"):
            subprocess.run(["rm", "-rf", "--", str(p)], check=True)
        (self.base / "sbuild-argv.json").unlink()
        r3, m3, w3, o3 = self.build("demo", "1.0+unity1", [["demo", "amd64"]], chroot=other,
                                    chroot_args=["--tested-with", str(tested)])
        self.assertEqual(r3.returncode, 2, r3.stderr)
        self.assertIn("the tested build used another chroot", r3.stderr)
        self.assertIsNone(m3)
        self.assertIsNone(self.sbuild_argv())

    def make_deb(self, directory, package, version, arch="amd64", source=None, package_type=None, filename=None):
        root = self.base / f".deb-{package}-{arch}-{len(list(self.base.iterdir()))}"
        (root / "DEBIAN").mkdir(parents=True)
        control = f"Package: {package}\nVersion: {version}\nArchitecture: {arch}\nMaintainer: t <t@example.com>\nDescription: t\n"
        if source:
            control += f"Source: {source}\n"
        if package_type:
            control += f"Package-Type: {package_type}\n"
        (root / "DEBIAN" / "control").write_text(control)
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (filename or f"{package}_{version.split(':', 1)[-1]}_{arch}.deb")
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(path)],
                       check=True, capture_output=True)
        return path

    def sbuild_argv(self):
        path = self.base / "sbuild-argv.json"
        return json.loads(path.read_text()) if path.exists() else None

    def test_without_extra_packages_unchanged(self):
        """No option: today's command, today's key set, no build-dependencies/."""
        r, m, w, o = self.build("demo", "1.0+unity1", [["demo", "amd64"]])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(m["build_command"], self.base_command())
        self.assertEqual(set(m), self.BASE_KEYS | {"chroot"})
        self.assertFalse((o / "build-dependencies").exists())
        self.assertEqual((o / m["log"]["file"]).read_text().splitlines()[0],
                         f"$ SBUILD_CONFIG={SBUILD_CONFIG} " + " ".join(self.base_command()))
        self.assertEqual(self.sbuild_argv(), self.base_command()[1:])

    def test_extra_packages_recorded_and_used(self):
        """Copies go to sbuild in order, the manifest records them, pool by content."""
        pool = self.base / "pool"
        # the binary's name starts with lib, its source (nux) does not: pool/main/n/nux/
        real_pool = self.make_deb(pool / "main" / "n" / "nux", "libnux-4.0-dev", "4.0.8-0ubuntu15+unity2",
                                  source="nux")
        inputs = self.base / "in"
        dev = inputs / real_pool.name
        dev.parent.mkdir()
        dev.write_bytes(real_pool.read_bytes())
        common = self.make_deb(inputs, "libnux-4.0-common", "4.0.8-0ubuntu15+unity2", arch="all", source="nux (4.0.8-0ubuntu15+unity2)")
        r, m, w, o = self.build("unity", "7.7.1-0ubuntu3+unity12", [["unity", "amd64"]], extra=[dev, common],
                                installed=["libnux-4.0-dev (= 4.0.8-0ubuntu15+unity2)",
                                           "libnux-4.0-common (= 4.0.8-0ubuntu15+unity2)", "zlib1g:amd64 (= 1:1.3)"],
                                pool_root=pool)
        self.assertEqual(r.returncode, 0, r.stderr)
        copies = [o / "build-dependencies" / dev.name, o / "build-dependencies" / common.name]
        self.assertEqual(self.sbuild_argv(), self.base_command()[1:] + [f"--extra-package={c}" for c in copies])
        self.assertEqual(m["build_command"], self.base_command() + [f"--extra-package={c}" for c in copies])
        self.assertEqual([e["file"] for e in m["build_dependencies"]],
                         [f"build-dependencies/{dev.name}", f"build-dependencies/{common.name}"])
        for entry, copy, given in zip(m["build_dependencies"], copies, (dev, common)):
            self.assertEqual(entry["sha256"], hashlib.sha256(copy.read_bytes()).hexdigest())
            self.assertEqual(entry["given_path"], str(given))
            self.assertEqual(entry["source"], "nux")
        self.assertTrue(m["build_dependencies"][0]["in_our_repository_pool"])
        self.assertEqual(m["build_dependencies"][0]["pool_path"], str(real_pool))
        self.assertFalse(m["build_dependencies"][1]["in_our_repository_pool"])
        self.assertNotIn("pool_path", m["build_dependencies"][1])
        self.assertEqual(m["artifacts"][0]["kind"], "source")  # artifacts untouched
        self.assertNotIn("build-dependencies", {a["file"].split("/")[0] for a in m["artifacts"]})

    def test_lib_source_pool_prefix(self):
        """A lib* source lives under pool/main/libX/<source>/."""
        pool = self.base / "pool"
        pooled = self.make_deb(pool / "main" / "libu" / "libunity", "libunity-dev", "7.1.4-6+unity1", source="libunity")
        dep = self.base / "in" / pooled.name
        dep.parent.mkdir()
        dep.write_bytes(pooled.read_bytes())
        r, m, w, o = self.build("unity", "7.7.1-0ubuntu3+unity12", [["unity", "amd64"]], extra=[dep],
                                installed=["libunity-dev (= 7.1.4-6+unity1)"], pool_root=pool)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(m["build_dependencies"][0]["in_our_repository_pool"])
        self.assertEqual(m["build_dependencies"][0]["pool_path"], str(pooled))

    def test_extra_package_not_used_refused(self):
        """Installed at another version, or not at all: exit 2, no manifest."""
        dev = self.make_deb(self.base / "in", "libnux-4.0-dev", "4.0.8-0ubuntu11", source="nux")
        for label, installed in {"older than the archive": ["libnux-4.0-dev (= 4.0.8-0ubuntu12)"],
                                 "absent": ["zlib1g (= 1:1.3)"]}.items():
            with self.subTest(case=label):
                for p in (self.base / "work", self.base / "out", self.base / "main-checkout"):
                    subprocess.run(["rm", "-rf", "--", str(p)], check=True)
                r, m, w, o = self.build("unity", "7.7.1-0ubuntu3+unity12", [["unity", "amd64"]], extra=[dev],
                                        installed=installed)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIsNone(m)
                self.assertIn("was not used by the build", r.stderr)

    def test_no_buildinfo_refused(self):
        dev = self.make_deb(self.base / "in", "libnux-4.0-dev", "4.0.8-0ubuntu15+unity2", source="nux")
        r, m, w, o = self.build("unity", "7.7.1-0ubuntu3+unity12", [["unity", "amd64"]], extra=[dev],
                                installed=["libnux-4.0-dev (= 4.0.8-0ubuntu15+unity2)"], no_buildinfo=True)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIsNone(m)
        self.assertIn(".buildinfo", r.stderr)

    def test_copy_changed_during_build_refused(self):
        dev = self.make_deb(self.base / "in", "libnux-4.0-dev", "4.0.8-0ubuntu15+unity2", source="nux")
        r, m, w, o = self.build("unity", "7.7.1-0ubuntu3+unity12", [["unity", "amd64"]], extra=[dev],
                                installed=["libnux-4.0-dev (= 4.0.8-0ubuntu15+unity2)"], tamper=True)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIsNone(m)
        self.assertIn("changed during the build", r.stderr)

    def refusal_cases(self):
        d = self.base / "cases"
        ok = self.make_deb(d / "a", "libfoo", "1.0", source="foo")
        same_name = self.make_deb(d / "b", "libfoo-other", "1.0", filename=ok.name)
        same_pkg = self.make_deb(d / "c", "libfoo", "1.0", filename="libfoo-copy.deb")
        not_deb = d / "notadeb.deb"
        not_deb.write_text("text")
        return {"missing file": [d / "missing.deb"], "directory": [d / "a"], "not a .deb": [not_deb],
                ".ddeb": [self.make_deb(d, "libfoo-dbgsym", "1.0", filename="libfoo-dbgsym_1.0_amd64.ddeb")],
                "udeb": [self.make_deb(d, "libfoo-udeb", "1.0", package_type="udeb")],
                "foreign architecture": [self.make_deb(d, "libfoo-arm", "1.0", arch="arm64")],
                "same basename twice": [ok, same_name], "same file twice": [ok, ok],
                "same package twice": [ok, same_pkg],
                "same package, other architecture": [ok, self.make_deb(d / "e", "libfoo", "1.0", arch="all")],
                "Source field with a path": [self.make_deb(d / "f", "libevil", "1.0", source="../../../etc")]}

    def test_refusals_before_sbuild(self):
        """Each is refused before sbuild runs (the stub never starts), no manifest."""
        for label in list(self.refusal_cases()):
            with self.subTest(case=label):
                self.tearDown(); self.setUp()
                extra = self.refusal_cases()[label]
                r, m, w, o = self.build("demo", "1.0+unity1", [["demo", "amd64"]], extra=extra)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIsNone(m)
                self.assertIsNone(self.sbuild_argv(), f"sbuild ran for: {label}")
                self.assertIn("--extra-package", r.stderr)
                # UNITY-20260929-014: a refusal leaves no copies behind
                left = sorted(q.name for q in o.iterdir()) if o.exists() else []
                self.assertEqual(left, [], f"left in the output for {label}: {left}")

    def test_relative_symlink_and_space_accepted(self):
        """A relative path (against the caller's cwd), a symlink and a space in the path."""
        target = self.make_deb(self.base / "dir with space", "libbar", "2.0", source="bar")
        link = self.base / "linked.deb"
        link.symlink_to(target)
        r, m, w, o = self.build("demo", "1.0+unity1", [["demo", "amd64"]],
                                extra=[Path("linked.deb")], cwd=self.base, installed=["libbar (= 2.0)"])
        self.assertEqual(r.returncode, 0, r.stderr)
        entry = m["build_dependencies"][0]
        self.assertEqual(entry["given_path"], "linked.deb")
        self.assertEqual(entry["resolved_path"], str(target))
        self.assertEqual(entry["file"], f"build-dependencies/{target.name}")
        self.tearDown(); self.setUp()
        target = self.make_deb(self.base / "dir with space", "libbar", "2.0", source="bar")
        r2, m2, w2, o2 = self.build("demo", "1.0+unity1", [["demo", "amd64"]], extra=[target],
                                    installed=["libbar (= 2.0)"])
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn(f"--extra-package={o2 / 'build-dependencies' / target.name}", m2["build_command"])


if __name__ == "__main__":
    unittest.main()
