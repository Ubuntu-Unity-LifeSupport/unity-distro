#!/usr/bin/env python3
"""UNITY-20260929-023: a package task reaches PUBLISHED through another task's
publish record (covering_record, check_own_build in scripts/taskctl.py).

A scratch git repository stands for the package source; a scratch directory
holds the publish records, written 0444 like the publisher does.
Run: python3 -m unittest discover -s scripts/tests
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import taskctl  # noqa: E402

TASK = "UNITY-20990101-002"
OTHER = "UNITY-20990101-001"
VERSION = "1:1.0+unity3"


def artifacts(version=VERSION, extra=()):
    base = [
        {"file": "demo_1.0+unity3.dsc", "sha256": "d" * 64, "kind": "source", "package": "demo",
         "version": version, "architecture": "source"},
        {"file": "demo_1.0+unity3.tar.xz", "sha256": "t" * 64, "kind": "source_file", "package": "demo",
         "version": version, "architecture": None},
        {"file": "demo-bin_1.0+unity3_amd64.deb", "sha256": "b" * 64, "kind": "binary", "package": "demo-bin",
         "version": version, "architecture": "amd64"},
        {"file": "demo_1.0+unity3_amd64.changes", "sha256": "c" * 64, "kind": "changes", "package": "demo",
         "version": version, "architecture": "amd64"},
    ]
    return base + list(extra)


class PublishedByTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.src = self.t / "src"
        self.src.mkdir()
        git = lambda *a: subprocess.run(["git", "-C", str(self.src), *a], check=True, capture_output=True, text=True).stdout.strip()
        git("init", "-q")
        git("config", "user.email", "t@example.invalid")
        git("config", "user.name", "t")
        (self.src / "f").write_text("1")
        git("add", "f")
        git("commit", "-q", "-m", "one")
        self.first = git("rev-parse", "HEAD")
        (self.src / "f").write_text("2")
        git("commit", "-q", "-am", "two")
        self.second = git("rev-parse", "HEAD")
        git("checkout", "-q", "-b", "side", self.first)
        (self.src / "g").write_text("x")
        git("add", "g")
        git("commit", "-q", "-m", "side")
        self.side = git("rev-parse", "HEAD")
        self.records = self.t / "records"
        self.records.mkdir()

    def tearDown(self):
        for path in self.records.glob("*"):
            os.chmod(path, 0o644)
        self.tmp.cleanup()

    def write_record(self, name=OTHER, mode=0o444, **overrides):
        record = {"schema": 1, "task_id": OTHER, "package": "demo", "candidate_version": VERSION,
                  "source_commit": self.second, "gate_file": "docs/x/gate/release-gate.json",
                  "artifacts": artifacts()}
        record.update(overrides)
        path = self.records / f"{name}.json"
        if path.exists():
            os.chmod(path, 0o644)
        path.write_text(json.dumps(record))
        os.chmod(path, mode)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def manifest(self, **overrides):
        m = {"task_id": TASK, "package": "demo", "candidate_version": VERSION, "source_commit": self.second,
             "source_repo": str(self.src), "artifacts": artifacts()}
        m.update(overrides)
        self.count = getattr(self, "count", 0) + 1
        path = self.t / f"manifest-{self.count}.json"
        path.write_text(json.dumps(m))
        return str(path)

    def evidence(self, digest, **overrides):
        data = {"package": "demo", "candidate_version": VERSION,
                "source_commit": "0274bc5 (free text, not used)",
                "published_by": {"task_id": OTHER, "record_sha256": digest}}
        data.update(overrides)
        if "build_manifest" not in overrides:
            data["build_manifest"] = self.manifest()
        return data

    def check(self, data):
        record, other = taskctl.covering_record(data, TASK, self.records)
        taskctl.check_own_build(data, TASK, record, self.t)
        return record, other

    def refused(self, data, fragment):
        with self.assertRaises(ValueError) as caught:
            self.check(data)
        self.assertIn(fragment, str(caught.exception))

    # accepted

    def test_same_commit_accepted(self):
        record, other = self.check(self.evidence(self.write_record()))
        self.assertEqual(other, OTHER)
        self.assertEqual(record["candidate_version"], VERSION)

    def test_ancestor_commit_accepted(self):
        digest = self.write_record()
        self.check(self.evidence(digest, build_manifest=self.manifest(source_commit=self.first)))

    # published_by shape

    def test_malformed_published_by(self):
        digest = self.write_record()
        for bad, fragment in (({"task_id": OTHER}, "{task_id, record_sha256}"),
                              ({"task_id": OTHER, "record_sha256": digest, "x": 1}, "{task_id, record_sha256}"),
                              ({"task_id": "../x", "record_sha256": digest}, "full UNITY-YYYYMMDD-NNN"),
                              ({"task_id": "UNITY-2099-1", "record_sha256": digest}, "full UNITY-YYYYMMDD-NNN"),
                              ({"task_id": OTHER, "record_sha256": "abc"}, "64 hex"),
                              ("UNITY-20990101-001", "{task_id, record_sha256}")):
            with self.subTest(bad=bad):
                self.refused(self.evidence(digest, published_by=bad), fragment)

    def test_self_reference(self):
        digest = self.write_record(name=TASK, task_id=TASK)
        self.refused(self.evidence(digest, published_by={"task_id": TASK, "record_sha256": digest}), "another task")

    # the record

    def test_no_record(self):
        self.refused(self.evidence("0" * 64), "publisher-created record is required")

    def test_sha256_mismatch(self):
        self.write_record()
        self.refused(self.evidence("0" * 64), "does not have the sha256")

    def test_writable_record(self):
        self.refused(self.evidence(self.write_record(mode=0o644)), "is writable")

    def test_symlink_record(self):
        real = self.t / "real.json"
        real.write_text(json.dumps({"schema": 1, "task_id": OTHER}))
        os.chmod(real, 0o444)
        (self.records / f"{OTHER}.json").symlink_to(real)
        self.refused(self.evidence(hashlib.sha256(real.read_bytes()).hexdigest()), "publisher-created record is required")

    def test_record_of_another_task(self):
        self.refused(self.evidence(self.write_record(task_id="UNITY-20990101-003")), "does not belong to")

    # the task's own build

    def test_package_or_version_mismatch(self):
        digest = self.write_record()
        self.refused(self.evidence(digest, build_manifest=self.manifest(package="other")), "package differs")
        self.refused(self.evidence(digest, build_manifest=self.manifest(candidate_version="1:1.0+unity2")),
                     "candidate_version differs")

    def test_manifest_missing_or_not_this_task(self):
        digest = self.write_record()
        data = self.evidence(digest)
        del data["build_manifest"]
        self.refused(data, "requires the task's own build_manifest")
        self.refused(self.evidence(digest, build_manifest=str(self.t / "nope.json")), "cannot read")
        self.refused(self.evidence(digest, build_manifest=self.manifest(task_id=OTHER)), "not this task's build")

    def test_commit_not_ancestor(self):
        digest = self.write_record()
        self.refused(self.evidence(digest, build_manifest=self.manifest(source_commit=self.side)),
                     "is not in the published source")

    def test_published_commit_missing_from_repo(self):
        digest = self.write_record(source_commit="1" * 40)
        self.refused(self.evidence(digest), "is not in")

    def test_short_or_text_commit(self):
        digest = self.write_record()
        self.refused(self.evidence(digest, build_manifest=self.manifest(source_commit=self.second[:7])), "40-hex")
        self.refused(self.evidence(self.write_record(source_commit="0274bc5 text")), "40-hex")

    def test_source_repo_not_git(self):
        (self.t / "plain").mkdir()
        digest = self.write_record()
        self.refused(self.evidence(digest, build_manifest=self.manifest(source_repo=str(self.t / "plain"))),
                     "not a git repository")

    def test_artifact_sets_must_match_both_ways(self):
        extra = {"file": "demo-extra_1.0+unity3_amd64.deb", "sha256": "e" * 64, "kind": "binary",
                 "package": "demo-extra", "version": VERSION, "architecture": "amd64"}
        digest = self.write_record(artifacts=artifacts(extra=[extra]))
        self.refused(self.evidence(digest), "extra [('demo-extra")
        digest = self.write_record()
        self.refused(self.evidence(digest, build_manifest=self.manifest(artifacts=artifacts(extra=[extra]))),
                     "missing [('demo-extra")

    def test_different_hashes_are_fine(self):
        """A different build of the same source: names match, hashes differ."""
        rebuilt = [dict(a, sha256="f" * 64) for a in artifacts()]
        self.check(self.evidence(self.write_record(), build_manifest=self.manifest(artifacts=rebuilt)))


if __name__ == "__main__":
    unittest.main()
