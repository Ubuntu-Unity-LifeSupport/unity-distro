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


if __name__ == "__main__":
    unittest.main()
