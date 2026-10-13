#!/usr/bin/env python3
"""UNITY-20260929-014: create_release_gate.py and publish_aptly.py, run for
real (harness: publish_harness.py), refuse a manifest whose build_dependencies fail the check, and treat a
good one exactly like a manifest without the key (both then stop at the same
later check, before any aptly call).

Each run happens in a temporary copy of the repository: scripts/ copied with
build_dependencies.POOL_ROOT pointed at a temporary pool, a git repository
with a local "remote", a package checkout under packages/, and a fake HOME
holding the task board and the task evidence. Safety: PATH starts with a
fake `aptly` that only records its arguments and exits 1, the test checks
that `aptly` resolves to it, and every case must leave its log empty - no
case gets as far as calling aptly.
Run: python3 -m unittest discover -s scripts/tests
"""

import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(HERE))
from publish_harness import PublishHarness, sha, TASK, PACKAGE, VERSION, SERIES, DEP_NAME  # noqa: E402


class ConsumersEndToEndTest(PublishHarness):
    """The harness (setUp, git, manifests, gate, board, publish) lives in
    publish_harness.py since the permission model phase 4; this file keeps
    the UNITY-20260929-014 cases."""

    def bad_cases(self):
        return {"sha256 of another file": lambda: [dict(self.entry, sha256="0" * 64)],
                "size true": lambda: [dict(self.entry, size=True)],
                "not in the pool": lambda: self.remove_from_pool(),
                "build-dependencies/ symlinked elsewhere": lambda: self.symlink_depdir()}

    def remove_from_pool(self):
        Path(self.entry["pool_path"]).unlink()
        return [self.entry]

    def symlink_depdir(self):
        elsewhere = self.build.parent / "elsewhere"
        (self.build / "build-dependencies").rename(elsewhere)
        (self.build / "build-dependencies").symlink_to(elsewhere)
        return [self.entry]

    def test_create_release_gate(self):
        without = self.create_release_gate(None)
        good = self.create_release_gate([self.entry])
        self.assertEqual(good.returncode, 2, good.stderr)
        # UNITY-20260929-020: the next check is now the chroot record (this fixture has none)
        self.assertIn("no chroot record", good.stderr)
        self.assertEqual((good.returncode, good.stderr), (without.returncode, without.stderr))
        for label in list(self.bad_cases()):
            with self.subTest(case=label):
                self.tearDown(); self.setUp()
                result = self.create_release_gate(self.bad_cases()[label]())
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("build dependenc", result.stderr)
                self.assertNotIn("no chroot record", result.stderr)

    def test_publish_aptly(self):
        without = self.publish(None)
        good = self.publish([self.entry])
        self.assertEqual(good.returncode, 2, good.stderr)
        self.assertNotIn("build dependenc", good.stderr)
        self.assertEqual((good.returncode, good.stderr), (without.returncode, without.stderr))
        for label in list(self.bad_cases()):
            with self.subTest(case=label):
                self.tearDown(); self.setUp()
                result = self.publish(self.bad_cases()[label]())
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("build dependenc", result.stderr)
                self.assertNotEqual(result.stderr, without.stderr)


sys.path.insert(0, str(SCRIPTS))
import tested_build  # noqa: E402


class TestedBuildEndToEndTest(ConsumersEndToEndTest):
    """UNITY-20260929-020: the real gate and publisher check the tested build
    (mode this_build here; the modes themselves are in test_tested_build.py)."""
    test_create_release_gate = None  # the parent's cases, not repeated here
    test_publish_aptly = None

    def setUp(self):
        super().setUp()
        deb = self.build / "demo_1.0+unity1_amd64.deb"
        (self.root / "rec" / "target-test.txt").write_text(f"installed {deb.name} on target-desktop\n")
        self.git(self.root, "add", "-A")
        self.git(self.root, "commit", "-qm", "target test record")
        self.debs = {deb.name: sha(deb)}
        self.manifest_extra = {"chroot": {"sha256": "a" * 64}}
        self.record_extra = {"tested_build": "this_build",
                             "target_test": {"record": "rec/target-test.txt", "debs": self.debs}}

    def gate_record(self, manifest):
        recorded, error = tested_build.check(self.record_extra, manifest, self.build, self.root)
        self.assertIsNone(error)
        return {"tested_build": recorded}

    def test_gate_checks_tested_build(self):
        result = self.create_release_gate([self.entry])
        self.assertIn("snapshot and distribution are required", result.stderr)  # past the check
        for case, extra, message in (
                ("no tested_build", {"tested_build": None}, "tested_build must be"),
                ("deb not of this build", {"target_test": {"record": "rec/target-test.txt",
                                                          "debs": {"demo_1.0+unity1_amd64.deb": "0" * 64}}},
                 "not binaries of this build"),
                ("no chroot record", None, "no chroot record")):
            with self.subTest(case=case):
                self.tearDown(); self.setUp()
                if extra is None:
                    self.manifest_extra = {}
                else:
                    self.record_extra = dict(self.record_extra, **extra)
                result = self.create_release_gate([self.entry])
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(message, result.stderr)

    def test_publish_checks_tested_build(self):
        self.gate_extra = self.gate_record
        good = self.publish([self.entry])
        self.assertEqual(good.returncode, 2, good.stderr)
        # past the check: the next one is the snapshot contract (this fixture has no source)
        self.assertIn("manifest must include the matching source and binary artifacts", good.stderr)
        cases = {
            "gate without tested_build": ({}, None, "no tested_build record"),
            "record changed after the gate": (self.gate_record, lambda: (self.root / "rec" / "target-test.txt").write_text(
                "installed demo_1.0+unity1_amd64.deb, edited after the gate\n"), "does not match"),
            "mode altered in the gate": (lambda m: {"tested_build": dict(self.gate_record(m)["tested_build"], mode="same_chroot")},
                                         None, "tested"),
        }
        for case, (extra, hook, message) in cases.items():
            with self.subTest(case=case):
                self.tearDown(); self.setUp()
                self.gate_extra, self.after_gate = extra, hook
                result = self.publish([self.entry])
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(message, result.stderr)
                self.assertNotIn("matching source and binary artifacts", result.stderr)

    def test_gate_requires_snapshot_content_in_the_view(self):
        """UNITY-20261008-005: the gate refuses a version_check view without content_sha256."""
        base = {"schema": 1, "tool": "apt_view.py", "mode": "full", "source_package": PACKAGE,
                "measured_at": "2099-01-01T00:00:00Z", "pockets": {}, "in_archive": False,
                "snapshot": {"name": "s", "list_sha256": "x", "content_sha256": "c"},
                "binaries": [{"package": PACKAGE, "version": VERSION, "architecture": "amd64", "apt_candidate": VERSION}]}
        for case, content, message in (("present", "c", "evidence file is missing"),
                                       ("missing", None, "does not record the snapshot's content_sha256"),
                                       ("empty", "", "does not record the snapshot's content_sha256")):
            with self.subTest(case=case):
                self.tearDown(); self.setUp()
                view = json.loads(json.dumps(base))
                if content is None:
                    del view["snapshot"]["content_sha256"]
                else:
                    view["snapshot"]["content_sha256"] = content
                (self.root / "rec" / "view.json").write_text(json.dumps(view))
                self.record_extra = dict(self.record_extra, version_check="rec/view.json",
                                         evidence={"evidence_card": "rec/card.md", "verification_record": "rec/v.md",
                                                   "patch_record": "rec/p.md"})
                manifest = self.write_manifest([self.entry])
                record = self.root / "rec" / "record.json"
                record.write_text(json.dumps({"task_id": TASK, "package": PACKAGE, "target_series": SERIES,
                                              "candidate_version": VERSION, "source_commit": self.commit,
                                              "verification_result": "PASS", "peer_notice": "ACK",
                                              "patch_and_decision_docs": "docs", "source_provenance": "PUSHED",
                                              **self.record_extra}))
                self.board("REVIEW")
                result = self.run_script("scripts/create_release_gate.py", "--record", str(record), "--build-manifest",
                                         str(manifest), "--snapshot", "s", "--distribution", "resolute",
                                         "--output", str(self.root / "rec" / "gate-out.json"))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(message, result.stderr)

    def untrack_buildinfo(self):
        """The file stays on disk, with its sha256, but is no longer in git."""
        with (self.root / ".gitignore").open("a") as f:
            f.write("*.buildinfo\n")
        self.git(self.root, "rm", "-q", "--cached", str(self.buildinfo.relative_to(self.root)))

    def test_gate_refuses_uncommitted_buildinfo(self):
        """UNITY-20261008-003: a gated build's .buildinfo must be committed."""
        self.git(self.root, "rm", "-q", "--cached", str(self.buildinfo.relative_to(self.root)))
        self.git(self.root, "commit", "-qm", "untrack")
        self.assertTrue(self.buildinfo.is_file())
        self.assertNotIn("buildinfo", self.git(self.root, "ls-files"))
        result = self.create_release_gate([self.entry])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("gated build's .buildinfo", result.stderr)
        self.assertIn("must be tracked, committed and unmodified", result.stderr)

    def test_publish_refuses_buildinfo_removed_from_git_after_the_gate(self):
        self.gate_extra, self.after_gate = self.gate_record, self.untrack_buildinfo
        result = self.publish([self.entry])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("gated build's .buildinfo", result.stderr)
        self.assertNotIn("matching source and binary artifacts", result.stderr)


if __name__ == "__main__":
    unittest.main()
