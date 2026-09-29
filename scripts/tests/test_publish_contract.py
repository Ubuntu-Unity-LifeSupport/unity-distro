#!/usr/bin/env python3
"""Tests for the manifest-to-snapshot contract of scripts/publish_aptly.py
(UNITY-20260927-050): every artifact kind a build_sbuild.py manifest can hold
is either expected in the gated snapshot or rejected by an explicit rule.
Run: python3 -m unittest discover -s scripts/tests
"""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import publish_fixtures  # noqa: E402

spec = importlib.util.spec_from_file_location("publish_aptly", HERE.parent / "publish_aptly.py")
publish_aptly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish_aptly)


class SnapshotContractTest(unittest.TestCase):
    def test_contract_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, case_dir, artifacts, expect in publish_fixtures.cases(tmp):
                with self.subTest(name):
                    names, error = publish_aptly.snapshot_expectations(
                        artifacts, case_dir, publish_fixtures.SRC, publish_fixtures.VER)
                    if isinstance(expect, list):
                        self.assertIsNone(error)
                        self.assertEqual(names, expect)
                    else:
                        self.assertIsNone(names)
                        self.assertIn(expect.split(": ", 1)[1], error)

    def test_binary_source(self):
        cases = [
            ({"Package": "demo", "Version": "1:1.0"}, ("demo", "1:1.0")),
            ({"Package": "demo-bin", "Version": "1:1.0", "Source": "demo"}, ("demo", "1:1.0")),
            ({"Package": "demo-bin", "Version": "1:1.0+b1", "Source": "demo (1:1.0)"}, ("demo", "1:1.0")),
        ]
        for fields, expected in cases:
            self.assertEqual(publish_aptly.binary_source(fields), expected)


class SourceFilesContractTest(unittest.TestCase):
    """UNITY-20260927-051: source files are exactly the .dsc's list, and the
    snapshot's source package must hold exactly the manifest's source files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def artifacts(self, dsc_lists, recorded):
        import hashlib
        (self.d / "demo_1.0.dsc").write_text("Source: demo\nChecksums-Sha256:\n" +
                                             "".join(f" {h} 1 {n}\n" for n, h in dsc_lists.items()) + "Files:\n")
        arts = [{"file": "demo_1.0.dsc", "kind": "source", "package": "demo", "version": "1:1.0",
                 "sha256": hashlib.sha256((self.d / "demo_1.0.dsc").read_bytes()).hexdigest()}]
        arts += [{"file": n, "kind": "source_file", "package": "demo", "version": "1:1.0", "sha256": h}
                 for n, h in recorded.items()]
        arts.append(publish_fixtures.deb(self.d, "demo-bin", "1:1.0", source="demo"))
        return arts

    def test_dsc_list_rule(self):
        cases = [({"demo_1.0.tar.xz": "aa"}, {"demo_1.0.tar.xz": "aa"}, None),
                 ({"demo_1.0.orig.tar.gz": "aa", "demo_1.0-1.debian.tar.xz": "bb"}, {"demo_1.0.orig.tar.gz": "aa"}, "not exactly"),
                 ({"demo_1.0.tar.xz": "aa"}, {"demo_1.0.tar.xz": "zz"}, "not exactly"),
                 ({}, {"stray.tar.xz": "aa"}, "not exactly")]
        for listed, recorded, error in cases:
            with self.subTest(listed=listed, recorded=recorded):
                names, got = publish_aptly.snapshot_expectations(self.artifacts(listed, recorded), self.d, "demo", "1:1.0")
                if error: self.assertIn(error, got)
                else: self.assertIsNone(got)

    def test_snapshot_source_package(self):
        arts = self.artifacts({"demo_1.0.tar.xz": "aa"}, {"demo_1.0.tar.xz": "aa"})
        dsc_hash = arts[0]["sha256"]
        same = {"demo_1.0.dsc": dsc_hash, "demo_1.0.tar.xz": "aa"}
        self.assertIsNone(publish_aptly.source_package_matches(arts, same))
        for bad in ({"demo_1.0.dsc": dsc_hash, "demo_1.0.tar.xz": "other"},
                    {"demo_1.0.dsc": dsc_hash},
                    dict(same, **{"demo_1.0.orig.tar.gz": "x"}),
                    {}):
            with self.subTest(bad=bad):
                self.assertIn("differs from the build", publish_aptly.source_package_matches(arts, bad))

    def test_aptly_view_parsed(self):
        text = (" 90e8 1770 demo_1.0.dsc\n 43ac 11799976 demo_1.0.tar.xz\n\n")
        self.assertEqual(publish_aptly.dsc_checksums("Checksums-Sha256:\n" + text),
                         {"demo_1.0.dsc": "90e8", "demo_1.0.tar.xz": "43ac"})


if __name__ == "__main__":
    unittest.main()
