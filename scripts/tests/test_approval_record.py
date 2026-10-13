#!/usr/bin/env python3
"""Unit tests for scripts/approval_record.py (permission model phase 4): the
strict reader, the writer, consumption with an outcome, and the live-source
reader. Everything runs in a temporary directory; nothing touches
~/coordinator or /srv/aptly.
Run: python3 -m unittest discover -s scripts/tests
"""

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("approval_record", HERE.parent / "approval_record.py")
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)

TASK = "UNITY-20990101-001"


def record(now, **changes):
    base = {"schema": 1, "kind": ar.KIND, "task_id": TASK, "approved_by": "C",
            "approved_at": ar.stamp(now), "not_after": ar.stamp(now + ar.WINDOW), "branch": "a/" + TASK,
            "gate_file": "docs/research/x/gate/release-gate.json", "gate_sha256": "a" * 64, "gate_commit": "b" * 40,
            "package": "demo", "candidate_version": "1.0+unity1", "source_repo": "packages/demo",
            "source_commit": "c" * 40, "source_tree_hash": "d" * 40, "snapshot": "unity-resolute-" + TASK,
            "distribution": "resolute", "prefix": ".", "build_manifest_sha256": "e" * 64,
            "evidence_manifest_sha256": "f" * 64,
            "artifacts": [{"file": "demo_1.0+unity1_amd64.deb", "sha256": "1" * 64, "kind": "binary"}],
            "known_gaps": [], "first_publication": False, "may_reference": ""}
    base.update(changes)
    return base


class ApprovalRecordTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ar.ROOT = Path(self.tmp.name) / "approvals"
        self.now = datetime(2099, 1, 1, 12, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()

    def write_raw(self, data, name=f"{TASK}.json", mode=0o600):
        ar.ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = ar.ROOT / name
        path.write_bytes(data)
        os.chmod(path, mode)
        return path

    def test_write_then_read(self):
        sha = ar.write(record(self.now))
        rec, got, raw = ar.read(TASK, self.now)
        self.assertEqual(got, sha)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), sha)
        self.assertEqual(rec["task_id"], TASK)
        self.assertEqual(oct(os.stat(ar.path_for(TASK)).st_mode & 0o777), "0o600")
        self.assertEqual(oct(os.stat(ar.ROOT).st_mode & 0o777), "0o700")

    def test_missing(self):
        with self.assertRaisesRegex(ar.ApprovalError, "no publication approval"):
            ar.read(TASK, self.now)

    def test_refusals(self):
        cases = {
            "mode 0644": (record(self.now), dict(mode=0o644), "mode 0600"),
            "other task in the file": (record(self.now, task_id="UNITY-20990101-002"), {}, "another task"),
            "approver A": (record(self.now, approved_by="A"), {}, "must be C's"),
            "missing key": ({k: v for k, v in record(self.now).items() if k != "branch"}, {}, "wrong keys"),
            "extra key": (dict(record(self.now), extra=1), {}, "wrong keys"),
            "null": (record(self.now, may_reference=None), {}, "null"),
            "control character": (record(self.now, may_reference="go\x01"), {}, "control character"),
            "future": (record(self.now + timedelta(minutes=10)), {}, "future"),
            "expired": (record(self.now - ar.WINDOW), {}, "expired"),
            "window": (record(self.now, not_after=ar.stamp(self.now + timedelta(hours=1))), {}, "exactly"),
            "first publication without reference": (record(self.now, first_publication=True), {}, "May's reference"),
            "short commit": (record(self.now, gate_commit="abc"), {}, "git object id"),
            "artifact without kind": (record(self.now, artifacts=[{"file": "x", "sha256": "1" * 64}]), {}, "artifacts"),
            "gap not a task": (record(self.now, known_gaps=["x"]), {}, "known_gaps"),
            "branch with ..": (record(self.now, branch="a/../b"), {}, "branch"),
        }
        for name, (rec, options, message) in cases.items():
            with self.subTest(name):
                self.tearDown(); self.setUp()
                data = (json.dumps(rec, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
                self.write_raw(data, **options)
                with self.assertRaisesRegex(ar.ApprovalError, message):
                    ar.read(TASK, self.now)

    def test_symlink_refused(self):
        ar.write(record(self.now))
        real = ar.path_for(TASK)
        other = ar.ROOT / "other.json"
        real.rename(other)
        real.symlink_to(other)
        with self.assertRaisesRegex(ar.ApprovalError, "not a link"):
            ar.read(TASK, self.now)

    def test_utf8_reference_accepted(self):
        ar.write(record(self.now, first_publication=True, may_reference="Май: GO в сессии A, 2026-10-09"))
        rec, _, _ = ar.read(TASK, self.now)
        self.assertTrue(rec["first_publication"])
        self.assertIn("Май", rec["may_reference"])

    def test_consume_and_outcome(self):
        ar.write(record(self.now))
        rec, sha, raw = ar.read(TASK, self.now)
        used, used_sha = ar.consume(TASK, raw, sha, "started", self.now)
        self.assertFalse(ar.path_for(TASK).exists())
        self.assertTrue(str(used).startswith(str(ar.used_dir())))
        got, got_sha = ar.read_used(used, TASK)
        self.assertEqual(got_sha, used_sha)
        self.assertEqual(got["outcome"], "started")
        self.assertEqual(oct(os.stat(used).st_mode & 0o777), "0o600")
        new_sha = ar.set_outcome(used, TASK, "published")
        got, got_sha = ar.read_used(used, TASK)
        self.assertEqual((got["outcome"], got_sha), ("published", new_sha))
        self.assertNotEqual(new_sha, used_sha)
        with self.assertRaisesRegex(ar.ApprovalError, "no publication approval"):
            ar.read(TASK, self.now)

    def test_consume_detects_a_rewrite(self):
        ar.write(record(self.now))
        rec, sha, raw = ar.read(TASK, self.now)
        ar.write(record(self.now, known_gaps=["UNITY-20990101-009"]))
        with self.assertRaisesRegex(ar.ApprovalError, "changed while the publisher ran"):
            ar.consume(TASK, raw, sha, "started", self.now)
        self.assertTrue(ar.path_for(TASK).exists())
        self.assertFalse(ar.used_dir().exists())

    def test_read_used_only_under_used(self):
        ar.write(record(self.now))
        with self.assertRaisesRegex(ar.ApprovalError, "under publication-approvals/used/"):
            ar.read_used(ar.path_for(TASK), TASK)

    def test_remove(self):
        ar.write(record(self.now))
        ar.remove(TASK)
        with self.assertRaisesRegex(ar.ApprovalError, "no publication approval to revoke"):
            ar.remove(TASK)


class KnownSourcesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.public = Path(self.tmp.name)
        self.dist = self.public / "dists" / "resolute"
        (self.dist / "main" / "binary-amd64").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def release(self, components="main", architectures="amd64"):
        (self.dist / "Release").write_text(f"Origin: . resolute\nComponents: {components}\n"
                                           f"Architectures: {architectures}\nDate: x\n")

    def test_sources_from_packages(self):
        self.release()
        (self.dist / "main" / "binary-amd64" / "Packages").write_text(
            "Package: gtk3-nocsd\nSource: gtk-nocsd (0~20260321+0b77e1b-1+unity2)\nVersion: 1\nArchitecture: all\n\n"
            "Package: hud\nVersion: 2\nArchitecture: amd64\n\n"
            "Package: libhud2\nSource: hud\nVersion: 2\nArchitecture: amd64\n")
        self.assertEqual(ar.known_sources(self.public, "resolute", "."), {"gtk-nocsd", "hud"})

    def test_other_components_refused(self):
        self.release(components="main universe")
        (self.dist / "main" / "binary-amd64" / "Packages").write_text("Package: hud\nVersion: 2\n")
        with self.assertRaisesRegex(ar.ApprovalError, "other components or architectures"):
            ar.known_sources(self.public, "resolute", ".")

    def test_missing_index_refused(self):
        self.release()
        with self.assertRaisesRegex(ar.ApprovalError, "cannot read the live Packages"):
            ar.known_sources(self.public, "resolute", ".")


if __name__ == "__main__":
    unittest.main()
