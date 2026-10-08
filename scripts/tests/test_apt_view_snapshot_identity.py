#!/usr/bin/env python3
"""UNITY-20261008-005: apt_view.snapshot_identity_lines identifies a snapshot by aptly
keys and per-package sha256, so a snapshot recreated under the same name with
other bytes changes content_sha256 while list_sha256 (names) stays equal.

The unit tests fake apt_view.aptly(); the integration tests run read-only
snapshot commands against a scratch root with its own -config (never /srv).
Run: python3 -m unittest discover -s scripts/tests
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import apt_view  # noqa: E402

TOOL = "apt" + "ly"


class FakeSearch:
    """Answers the two snapshot searches snapshot_identity_lines makes."""

    def __init__(self, binaries, sources):
        self.binaries, self.sources, self.calls = binaries, sources, []

    def __call__(self, config, *args):
        self.calls.append(args)
        assert args[:2] == ("snapshot", "search"), args
        if args[-1] == apt_view.ALL_PACKAGES:
            return "".join(f"{k}|{d}\n" for k, d in self.binaries) + "".join(f"{k}|\n" for k in self.sources)
        assert args[-1] == "$Architecture (source)", args
        return "".join(f"{k}\n" + "".join(f" {e}\n" for e in entries) for k, entries in self.sources.items())


class SnapshotContentUnitTest(unittest.TestCase):
    def content(self, fake):
        saved = apt_view.aptly
        apt_view.aptly = fake
        try:
            return apt_view.snapshot_identity_lines(None, "s")
        finally:
            apt_view.aptly = saved

    def test_lines(self):
        fake = FakeSearch([("Pamd64 demo-bin 1.0 aa", "1" * 64), ("Pall demo-data 1.0 bb", "2" * 64)],
                          {"Psource demo 1.0 cc": [f"{'4' * 64} 20 demo_1.0.tar.xz", f"{'3' * 64} 10 demo_1.0.dsc"]})
        self.assertEqual(self.content(fake), [
            "Pall demo-data 1.0 bb|" + "2" * 64,
            "Pamd64 demo-bin 1.0 aa|" + "1" * 64,
            f"Psource demo 1.0 cc|{'3' * 64} 10 demo_1.0.dsc,{'4' * 64} 20 demo_1.0.tar.xz"])

    def test_no_sources_no_second_search(self):
        fake = FakeSearch([("Pamd64 demo-bin 1.0 aa", "1" * 64)], {})
        self.assertEqual(len(self.content(fake)), 1)
        self.assertEqual(len(fake.calls), 1)

    def test_binary_without_sha256_refused(self):
        with self.assertRaisesRegex(RuntimeError, "has no SHA256"):
            self.content(FakeSearch([("Pamd64 demo-bin 1.0 aa", "")], {}))

    def test_source_without_checksums_refused(self):
        with self.assertRaisesRegex(RuntimeError, "has no Checksums-Sha256"):
            self.content(FakeSearch([], {"Psource demo 1.0 cc": []}))

    def test_source_keys_differ_between_searches_refused(self):
        class Drift(FakeSearch):
            def __call__(self, config, *args):
                out = super().__call__(config, *args)
                return out.replace("Psource demo 1.0 cc", "Psource demo 1.0 dd") if args[-1] != apt_view.ALL_PACKAGES else out
        with self.assertRaisesRegex(RuntimeError, "differ between the two searches"):
            self.content(Drift([], {"Psource demo 1.0 cc": [f"{'3' * 64} 10 demo_1.0.dsc"]}))


@unittest.skipUnless(shutil.which(TOOL) and shutil.which("dpkg-source") and os.geteuid() != 0,
                     "needs the repository tool, dpkg-source and a non-root user")
class SnapshotContentScratchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.conf = self.t / "conf.json"
        self.conf.write_text(json.dumps({"rootDir": str(self.t / "root"), "gpgDisableSign": True,
                                         "gpgDisableVerify": True}))
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args):
        return subprocess.run([TOOL, f"-config={self.conf}", *args], check=True, capture_output=True, text=True).stdout

    def deb(self, name, marker, arch="amd64"):
        self.n += 1
        root = self.t / f".b{self.n}"
        (root / "DEBIAN").mkdir(parents=True)
        (root / "DEBIAN" / "control").write_text(f"Package: {name}\nVersion: 1.0+unity1\nArchitecture: {arch}\n"
                                                 f"Maintainer: t <t@example.com>\nDescription: t {marker}\n")
        out = self.t / f"out{self.n}"
        out.mkdir()
        path = out / f"{name}_1.0+unity1_{arch}.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(path)],
                       check=True, capture_output=True)
        return path

    def source(self, marker, fmt="3.0 (native)"):
        """A source package (native: .dsc + .tar.xz; quilt: .dsc + orig + debian tarballs)."""
        self.n += 1
        work = self.t / f"src{self.n}"
        src = work / "demo-1.0"
        (src / "debian" / "source").mkdir(parents=True)
        (src / "debian" / "source" / "format").write_text(fmt + "\n")
        (src / "debian" / "control").write_text(
            "Source: demo\nMaintainer: t <t@example.com>\n\nPackage: demo-bin\nArchitecture: amd64\nDescription: t\n")
        version = "1.0-1" if "quilt" in fmt else "1.0"
        (src / "debian" / "changelog").write_text(
            f"demo ({version}) resolute; urgency=medium\n\n  * {marker}\n\n -- t <t@example.com>  Tue, 29 Sep 2026 00:00:00 +0000\n")
        (src / "README").write_text(marker + "\n")
        if "quilt" in fmt:
            subprocess.run(["tar", "-cJf", str(work / "demo_1.0.orig.tar.xz"), "-C", str(work), "--exclude=debian",
                            "demo-1.0"], check=True)
        subprocess.run(["dpkg-source", "-b", "demo-1.0"], cwd=work, check=True, capture_output=True)
        return next(work.glob("*.dsc"))

    def snapshot(self, name, *files):
        self.n += 1
        repo = f"r-{name}-{self.n}"
        self.run_tool("repo", "create", repo)
        self.run_tool("repo", "add", repo, *map(str, files))
        self.run_tool("snapshot", "create", name, "from", "repo", repo)

    def identity(self, name):
        listed, _ = apt_view.snapshot_model(str(self.conf), name)
        return listed, apt_view.snapshot_identity_lines(str(self.conf), name)

    def recreated(self, before_files, after_files):
        self.snapshot("s", *before_files)
        before = self.identity("s")
        self.run_tool("snapshot", "drop", "s")
        self.snapshot("s", *after_files)
        return before, self.identity("s")

    def test_binary_recreated_with_other_bytes(self):
        (names1, content1), (names2, content2) = self.recreated([self.deb("demo-bin", "gated")],
                                                                [self.deb("demo-bin", "rebuilt")])
        self.assertEqual(names1, names2)
        self.assertNotEqual(content1, content2)

    def test_source_recreated_with_other_bytes(self):
        bin1 = self.deb("demo-bin", "same")
        (names1, content1), (names2, content2) = self.recreated([self.source("one"), bin1], [self.source("two"), bin1])
        self.assertEqual(names1, names2)
        self.assertNotEqual(content1, content2)
        self.assertEqual([l for l in content1 if not l.startswith("Psource")],
                         [l for l in content2 if not l.startswith("Psource")])

    def test_quilt_source_lists_every_file_and_query_matches_all(self):
        dsc = self.source("q", fmt="3.0 (quilt)")
        self.snapshot("s", dsc, self.deb("demo-bin", "b"), self.deb("name", "literally named name"),
                      self.deb("demo-data", "d", arch="all"))
        listed, content = self.identity("s")
        self.assertEqual(len(content), len(listed))  # every record, including the package called "name"
        source = [l for l in content if l.startswith("Psource ")]
        self.assertEqual(len(source), 1)
        entries = source[0].split("|", 1)[1].split(",")
        self.assertEqual(sorted(e.rsplit(" ", 1)[1] for e in entries),
                         sorted(["demo_1.0-1.dsc", "demo_1.0.orig.tar.xz", "demo_1.0-1.debian.tar.xz"]))
        dsc_entry = next(e for e in entries if e.endswith(".dsc"))
        self.assertEqual(dsc_entry.split()[0], hashlib.sha256(dsc.read_bytes()).hexdigest())
        binaries = [l for l in content if not l.startswith("Psource ")]
        self.assertTrue(all(len(l.rsplit("|", 1)[1]) == 64 for l in binaries))

    def test_debs_only_snapshot(self):
        self.snapshot("s", self.deb("demo-bin", "x"))
        self.assertEqual(len(self.identity("s")[1]), 1)


if __name__ == "__main__":
    unittest.main()
