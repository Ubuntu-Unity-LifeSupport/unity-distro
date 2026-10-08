#!/usr/bin/env python3
"""UNITY-20260929-023, UNITY-20261008-003: a package task reaches PUBLISHED
through another task's publish record (covering_record, check_own_build in
scripts/taskctl.py). Its own build must be the published bytes (rule 1) or
buildinfo_identical to the published build, which is read through the
record's gate (rule 2); an ancestor commit no longer counts.

A scratch meta repository holds the committed manifests, gate and .buildinfo
files; a scratch directory holds the publish records, written 0444 like the
publisher does.
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
COMMIT = "a" * 40
TREE = "b" * 40
IBD = " base-files (= 14ubuntu6.2),\n libc6 (= 2.43-2ubuntu2.4)\n"
BUILDINFO = "demo_1.0+unity3_amd64.buildinfo"


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def buildinfo_text(ibd=IBD, version=VERSION):
    return (f"Format: 1.0\nSource: demo\nBinary: demo-bin\nArchitecture: amd64\nVersion: {version}\n"
            f"Build-Architecture: amd64\nInstalled-Build-Depends:\n{ibd}")


def artifacts(seed="", version=VERSION, extra=(), buildinfo=None):
    """Source and binary records whose sha256 depends on seed (a rebuild has another seed)."""
    base = [
        {"file": "demo_1.0+unity3.dsc", "sha256": sha("dsc" + seed), "kind": "source", "package": "demo",
         "version": version, "architecture": "source"},
        {"file": "demo_1.0+unity3.tar.xz", "sha256": sha("tar" + seed), "kind": "source_file", "package": "demo",
         "version": version, "architecture": None},
        {"file": "demo-bin_1.0+unity3_amd64.deb", "sha256": sha("deb" + seed), "kind": "binary",
         "package": "demo-bin", "version": version, "architecture": "amd64"},
        {"file": "demo_1.0+unity3_amd64.changes", "sha256": sha("changes" + seed), "kind": "changes",
         "package": "demo", "version": version, "architecture": "amd64"},
    ]
    if buildinfo is not None:
        base.append({"file": BUILDINFO, "sha256": sha(buildinfo), "kind": "buildinfo", "package": "demo",
                     "version": version, "architecture": "amd64"})
    return base + list(extra)


class PublishedByTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.records = self.t / "records"
        self.records.mkdir()
        # the repository taskctl lives in: manifests, gate and .buildinfo must be committed there
        self.meta = self.t / "meta"
        self.meta.mkdir()
        self.mgit("init", "-q")
        self.mgit("config", "user.email", "t@example.invalid")
        self.mgit("config", "user.name", "t")
        self.count = 0
        self.published = self.write_build("published", artifacts(buildinfo=buildinfo_text()), buildinfo_text())
        self.gate = self.write_file("docs/pub/gate/release-gate.json", json.dumps(
            {"schema": 1, "task_id": OTHER, "build_manifest": {"file": self.published, "sha256": self.sha_of(self.published)}}))

    def tearDown(self):
        for path in self.records.glob("*"):
            os.chmod(path, 0o644)
        self.tmp.cleanup()

    def mgit(self, *args):
        return subprocess.run(["git", "-C", str(self.meta), *args], check=True, capture_output=True, text=True).stdout

    def sha_of(self, rel):
        return sha((self.meta / rel).read_bytes())

    def write_file(self, rel, text, commit=True):
        path = self.meta / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if commit:
            self.mgit("add", rel)
            self.mgit("commit", "-q", "-m", rel)
        return rel

    def write_build(self, name, arts, buildinfo=None, commit_buildinfo=True, task_id=OTHER, **overrides):
        """A build directory docs/<name>/ with its manifest and, if given, its .buildinfo."""
        m = {"schema": 1, "task_id": task_id, "package": "demo", "candidate_version": VERSION,
             "source_commit": COMMIT, "source_tree_hash": TREE, "artifacts": arts}
        commit = overrides.pop("_commit", True)
        m.update(overrides)
        if buildinfo is not None:
            self.write_file(f"docs/{name}/{BUILDINFO}", buildinfo, commit=commit_buildinfo)
        return self.write_file(f"docs/{name}/manifest.json", json.dumps(m), commit=commit)

    def write_record(self, name=OTHER, mode=0o444, **overrides):
        record = {"schema": 1, "task_id": OTHER, "package": "demo", "candidate_version": VERSION,
                  "source_commit": COMMIT, "gate_file": self.gate, "gate_sha256": self.sha_of(self.gate),
                  "artifacts": artifacts(buildinfo=buildinfo_text())}
        record.update(overrides)
        path = self.records / f"{name}.json"
        if path.exists():
            os.chmod(path, 0o644)
        path.write_text(json.dumps(record))
        os.chmod(path, mode)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def manifest(self, seed="", buildinfo=None, commit_buildinfo=True, **overrides):
        """The covered task's own build manifest (seed "" = the published bytes)."""
        self.count += 1
        arts = overrides.pop("artifacts", None) or artifacts(seed, buildinfo=buildinfo)
        task_id = overrides.pop("task_id", TASK)
        return self.write_build(f"own-{self.count}", arts, buildinfo, commit_buildinfo, task_id=task_id, **overrides)

    def rebuild(self, ibd=IBD, **overrides):
        """Another build of the same commit: other bytes, its own .buildinfo."""
        return self.manifest(seed="rebuilt", buildinfo=buildinfo_text(ibd), **overrides)

    def evidence(self, digest, **overrides):
        data = {"task_id": TASK, "package": "demo", "candidate_version": VERSION,
                "verification_result": "PASS", "review_status": "REVIEWED",
                "source_commit": "0274bc5 (free text, not used)",
                "published_by": {"task_id": OTHER, "record_sha256": digest}}
        data.update(overrides)
        if "build_manifest" not in overrides:
            data["build_manifest"] = self.manifest()
        return data

    def check(self, data):
        record, other = taskctl.covering_record(data, TASK, self.records)
        taskctl.check_own_build(data, TASK, record, self.meta)
        return record, other

    def refused(self, data, fragment):
        with self.assertRaises(ValueError) as caught:
            self.check(data)
        self.assertIn(fragment, str(caught.exception))
        return str(caught.exception)

    # accepted

    def test_same_bytes_accepted(self):
        """Rule 1 (the UNITY-20260927-052 case): no .buildinfo needed."""
        record, other = self.check(self.evidence(self.write_record()))
        self.assertEqual(other, OTHER)
        self.assertEqual(record["candidate_version"], VERSION)

    def test_rebuild_buildinfo_identical_accepted(self):
        """Rule 2 (the UNITY-20261002-011 case): same commit, other bytes, identical .buildinfo."""
        self.check(self.evidence(self.write_record(), build_manifest=self.rebuild()))

    # refused under the new rule

    def test_rebuild_other_installed_build_depends_refused(self):
        """The UNITY-20260928-020 case: same commit and tree, another toolchain."""
        error = self.refused(self.evidence(self.write_record(), build_manifest=self.rebuild(
            ibd=" base-files (= 14ubuntu6),\n libc6 (= 2.43-2ubuntu2)\n")), "Installed-Build-Depends")
        self.assertIn("not the published bytes", error)
        self.assertIn("demo-bin_1.0+unity3_amd64.deb", error)

    def test_ancestor_commit_refused(self):
        self.refused(self.evidence(self.write_record(), build_manifest=self.rebuild(source_commit="c" * 40)),
                     "differ in source_commit")

    def test_other_tree_or_build_dependencies_refused(self):
        digest = self.write_record()
        self.refused(self.evidence(digest, build_manifest=self.rebuild(source_tree_hash="d" * 40)),
                     "differ in source_tree_hash")
        extra = [{"package": "libx-dev", "version": "1", "architecture": "amd64", "sha256": "e" * 64}]
        self.refused(self.evidence(digest, build_manifest=self.rebuild(build_dependencies=extra)),
                     "differ in build_dependencies")

    def test_buildinfo_identity_field_refused(self):
        other = buildinfo_text().replace("Build-Architecture: amd64", "Build-Architecture: arm64")
        self.refused(self.evidence(self.write_record(), build_manifest=self.manifest(seed="r", buildinfo=other)),
                     "differ in Build-Architecture")

    def test_uncommitted_buildinfo_refused(self):
        digest = self.write_record()
        self.refused(self.evidence(digest, build_manifest=self.rebuild(commit_buildinfo=False)),
                     "must be tracked, committed and unmodified")

    def test_published_buildinfo_uncommitted_refused(self):
        self.mgit("rm", "-q", "--cached", f"docs/published/{BUILDINFO}")
        self.mgit("commit", "-q", "-m", "untrack")
        self.refused(self.evidence(self.write_record(), build_manifest=self.rebuild()),
                     "the published .buildinfo")

    def test_buildinfo_other_sha_refused(self):
        rel = self.rebuild()
        bi = f"{Path(rel).parent}/{BUILDINFO}"
        self.write_file(bi, buildinfo_text() + " \n")  # committed, but not what the manifest records
        self.refused(self.evidence(self.write_record(), build_manifest=rel), "does not match the sha256")

    def test_two_or_no_buildinfo_refused(self):
        digest = self.write_record()
        bi = buildinfo_text()
        two = artifacts("rebuilt", buildinfo=bi) + [dict(artifacts(buildinfo=bi)[-1], file="second.buildinfo")]
        self.refused(self.evidence(digest, build_manifest=self.manifest(artifacts=two, buildinfo=bi)),
                     "lists 2 .buildinfo files")
        self.refused(self.evidence(digest, build_manifest=self.manifest(seed="rebuilt")), "lists 0 .buildinfo files")

    def test_gate_sha_mismatch_refused(self):
        self.refused(self.evidence(self.write_record(gate_sha256="0" * 64), build_manifest=self.rebuild()),
                     "gate_sha256")

    def test_gate_of_another_task_refused(self):
        gate = self.write_file("docs/pub/gate/other-gate.json", json.dumps(
            {"schema": 1, "task_id": "UNITY-20990101-009",
             "build_manifest": {"file": self.published, "sha256": self.sha_of(self.published)}}))
        digest = self.write_record(gate_file=gate, gate_sha256=self.sha_of(gate))
        self.refused(self.evidence(digest, build_manifest=self.rebuild()), "belongs to another task")

    def test_gate_uncommitted_or_missing_refused(self):
        gate = self.write_file("docs/pub/gate/loose.json", (self.meta / self.gate).read_text(), commit=False)
        digest = self.write_record(gate_file=gate, gate_sha256=self.sha_of(gate))
        self.refused(self.evidence(digest, build_manifest=self.rebuild()), "must be tracked")
        digest = self.write_record(gate_file="docs/none.json")
        self.refused(self.evidence(digest, build_manifest=self.rebuild()), "does not exist")

    def test_published_manifest_sha_mismatch_refused(self):
        gate = self.write_file("docs/pub/gate/bad-gate.json", json.dumps(
            {"schema": 1, "task_id": OTHER, "build_manifest": {"file": self.published, "sha256": "0" * 64}}))
        digest = self.write_record(gate_file=gate, gate_sha256=self.sha_of(gate))
        self.refused(self.evidence(digest, build_manifest=self.rebuild()), "does not match the release gate")

    def test_artifact_sets_compared_by_bytes_both_ways(self):
        extra = {"file": "demo-extra_1.0+unity3_amd64.deb", "sha256": "e" * 64, "kind": "binary",
                 "package": "demo-extra", "version": VERSION, "architecture": "amd64"}
        digest = self.write_record(artifacts=artifacts(extra=[extra]))
        self.refused(self.evidence(digest), "extra [('demo-extra")
        digest = self.write_record()
        self.refused(self.evidence(digest, build_manifest=self.manifest(artifacts=artifacts(extra=[extra]))),
                     "missing [('demo-extra")

    def test_names_equal_bytes_differ_without_buildinfo_refused(self):
        """What the old rule accepted: the same names with other hashes."""
        self.refused(self.evidence(self.write_record(), build_manifest=self.manifest(seed="rebuilt")),
                     "not the published bytes")

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
        self.refused(self.evidence(digest, build_manifest="docs/nope.json"), "does not exist")
        self.refused(self.evidence(digest, build_manifest=self.manifest(task_id=OTHER)), "not this task's build")

    def test_manifest_must_be_committed_in_the_repository(self):
        """Verifier round 1 of UNITY-20260929-023: an unbound manifest let a task claim any build."""
        digest = self.write_record()
        self.refused(self.evidence(digest, build_manifest=self.manifest(_commit=False)), "must be tracked")
        outside = self.t / "outside.json"
        outside.write_text("{}")
        self.refused(self.evidence(digest, build_manifest=str(outside)), "repository-relative")
        self.refused(self.evidence(digest, build_manifest="../outside.json"), "repository-relative")
        committed = self.manifest()
        (self.meta / committed).write_text((self.meta / committed).read_text() + " ")
        self.refused(self.evidence(digest, build_manifest=committed), "must be tracked")

    def test_own_verification_required(self):
        digest = self.write_record()
        for overrides in ({"verification_result": "FAIL"}, {"verification_result": None},
                          {"review_status": None}, {"review_status": "PENDING"}):
            with self.subTest(overrides=overrides):
                self.refused(self.evidence(digest, **overrides), "verification_result PASS and review_status")

    def test_evidence_task_id_must_be_this_task(self):
        digest = self.write_record()
        self.refused(self.evidence(digest, task_id=OTHER), "task_id must be this task")

    def test_unhashable_artifact_field_is_a_refusal_not_a_crash(self):
        odd = artifacts()
        odd[2] = dict(odd[2], sha256=["x"])
        self.refused(self.evidence(self.write_record(), build_manifest=self.manifest(artifacts=odd)), "not the published bytes")


if __name__ == "__main__":
    unittest.main()
