#!/usr/bin/env python3
"""Permission model phase 4: C's publication approval, end to end through the
real taskctl.py and publish_aptly.py in the harness (nothing reaches aptly),
plus the consume-and-switch step with a fake runner and taskctl's PUBLISHED
authorization check.
Run: python3 -m unittest discover -s scripts/tests
"""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from publish_harness import PublishHarness, TASK, PACKAGE, VERSION  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE.parent / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ApprovalEndToEndTest(PublishHarness):
    def approvals(self):
        return self.home / "coordinator" / "publication-approvals"

    def test_publisher_refuses_without_approval(self):
        result = self.publish([self.entry], approved=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("no publication approval by C", result.stderr)
        self.assertNotIn("evidence manifest", result.stderr)

    def test_publisher_accepts_the_approval_and_goes_on(self):
        result = self.publish([self.entry])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("publication approval", result.stderr)
        self.assertNotIn("origin/main", result.stderr)
        self.assertTrue((self.approvals() / f"{TASK}.json").is_file())
        record = json.loads((self.approvals() / f"{TASK}.json").read_text())
        self.assertEqual(record["approved_by"], "C")
        self.assertEqual(record["gate_commit"], self.git(self.root, "rev-parse", "HEAD"))
        self.assertFalse(record["first_publication"])
        self.assertEqual([a["file"] for a in record["artifacts"]],
                         ["demo_1.0+unity1_amd64.deb", "demo_1.0+unity1_amd64.buildinfo"])
        self.assertIn("C APPROVE publication", (self.home / "AGENTS-LOG.md").read_text())

    def test_only_c_approves(self):
        self.write_gate([self.entry])
        for actor in ("A", "B", "May"):
            with self.subTest(actor=actor):
                result = self.approve(actor=actor)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("only C approves", result.stderr)
        self.assertFalse(self.approvals().exists())

    def test_board_state_must_be_ready(self):
        gate = self.write_gate([self.entry])
        self.board("REVIEW", str(self.home / "evidence.json"))
        result = self.approve()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("READY_TO_PUBLISH", result.stderr)

    def test_same_gate_twice_refused_new_gate_replaces(self):
        gate = self.write_gate([self.entry])
        self.assertEqual(self.approve().returncode, 0)
        again = self.approve()
        self.assertEqual(again.returncode, 2, again.stderr)
        self.assertIn("already exists", again.stderr)
        # the gate is regenerated: a new sha, the approval is replaced and logged
        content = json.loads(gate.read_text())
        content["peer_notice"] = "COORDINATOR_CONFIRMED_NO_CONFLICT"
        gate.write_text(json.dumps(content))
        self.git(self.root, "add", "rec/gate.json")
        self.git(self.root, "commit", "-qm", "gate again")
        self.git(self.root, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.git(self.root, "fetch", "-q", "origin")
        replaced = self.approve()
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertIn("replaces", (self.home / "AGENTS-LOG.md").read_text())

    def test_branch_must_hold_head(self):
        self.write_gate([self.entry])
        result = self.approve(branch="a/elsewhere")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("origin/a/elsewhere", result.stderr)

    def test_commit_after_approval_refused_by_the_publisher(self):
        gate = self.write_gate([self.entry])
        self.assertEqual(self.approve().returncode, 0)
        (self.root / "rec" / "note.txt").write_text("after the approval\n")
        self.git(self.root, "add", "rec/note.txt")
        self.git(self.root, "commit", "-qm", "after the approval")
        self.git(self.root, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.git(self.root, "fetch", "-q", "origin")
        result = self.run_script("scripts/publish_aptly.py", "--gate", str(gate))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("differs from the approved gate commit", result.stderr)

    def test_revoked_approval(self):
        gate = self.write_gate([self.entry])
        self.assertEqual(self.approve().returncode, 0)
        revoked = self.run_script("scripts/taskctl.py", "revoke-publication", TASK, "--actor", "C")
        self.assertEqual(revoked.returncode, 0, revoked.stderr)
        result = self.run_script("scripts/publish_aptly.py", "--gate", str(gate))
        self.assertIn("no publication approval by C", result.stderr)
        denied = self.run_script("scripts/taskctl.py", "revoke-publication", TASK, "--actor", "A")
        self.assertIn("only C revokes", denied.stderr)

    def test_older_publication_tools_refused(self):
        """A task branch forked before a tool change on main: origin/main has a
        newer scripts/apt_view.py than HEAD (design rounds 3-5)."""
        self.write_gate([self.entry])
        tool = self.root / "scripts" / "apt_view.py"
        tool.write_text(tool.read_text() + "\n# newer on main\n")
        self.git(self.root, "add", "scripts/apt_view.py")
        self.git(self.root, "commit", "-qm", "tool change on main")
        self.git(self.root, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.git(self.root, "fetch", "-q", "origin")
        self.git(self.root, "reset", "-q", "--hard", "HEAD~1")
        result = self.approve()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("scripts/apt_view.py at HEAD differs from origin/main", result.stderr)

    def test_modified_tool_in_the_working_tree_refused_by_the_publisher(self):
        gate = self.write_gate([self.entry])
        self.assertEqual(self.approve().returncode, 0)
        tool = self.root / "scripts" / "version_safety.py"
        tool.write_text(tool.read_text() + "\n# edited\n")
        result = self.run_script("scripts/publish_aptly.py", "--gate", str(gate))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("modified in the working tree", result.stderr)

    def test_approval_of_another_gate_refused_by_the_publisher(self):
        gate = self.write_gate([self.entry])
        self.assertEqual(self.approve().returncode, 0)
        path = self.approvals() / f"{TASK}.json"
        record = json.loads(path.read_text())
        record["gate_sha256"] = "0" * 64
        path.write_text(json.dumps(record))
        result = self.run_script("scripts/publish_aptly.py", "--gate", str(gate))
        self.assertIn("another release gate", result.stderr)

    def test_approval_with_mode_0644_refused(self):
        gate = self.write_gate([self.entry])
        self.assertEqual(self.approve().returncode, 0)
        os.chmod(self.approvals() / f"{TASK}.json", 0o644)
        result = self.run_script("scripts/publish_aptly.py", "--gate", str(gate))
        self.assertIn("mode 0600", result.stderr)


class FirstPublicationTest(PublishHarness):
    live_sources = ("other",)

    def test_first_publication_needs_mays_reference(self):
        self.write_gate([self.entry])
        result = self.approve()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("first publication needs", result.stderr)
        result = self.approve("--may-reference", "May: GO in session A, 2099-01-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((self.home / "coordinator" / "publication-approvals" / f"{TASK}.json").read_text())
        self.assertTrue(record["first_publication"])
        self.assertIn("FIRST PUBLICATION", (self.home / "AGENTS-LOG.md").read_text())


class ConsumeAndSwitchTest(unittest.TestCase):
    """The step between START and the publish record, with a fake aptly."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pa = load("publish_aptly")
        self.ar = self.pa.approval_record
        self.ar.ROOT = Path(self.tmp.name) / "approvals"
        self.now = datetime(2099, 1, 1, tzinfo=timezone.utc)
        base = {"schema": 1, "kind": self.ar.KIND, "task_id": TASK, "approved_by": "C",
                "approved_at": self.ar.stamp(self.now), "not_after": self.ar.stamp(self.now + self.ar.WINDOW),
                "branch": "a/" + TASK, "gate_file": "rec/gate.json", "gate_sha256": "a" * 64, "gate_commit": "b" * 40,
                "package": PACKAGE, "candidate_version": VERSION, "source_repo": "packages/demo",
                "source_commit": "c" * 40, "source_tree_hash": "d" * 40, "snapshot": "snap",
                "distribution": "resolute", "prefix": ".", "build_manifest_sha256": "e" * 64,
                "evidence_manifest_sha256": "f" * 64,
                "artifacts": [{"file": "x.deb", "sha256": "1" * 64, "kind": "binary"}],
                "known_gaps": [], "first_publication": False, "may_reference": ""}
        self.ar.write(base)
        self.approval = self.ar.read(TASK, self.now)
        self.logged = []

    def tearDown(self):
        self.tmp.cleanup()

    def run_switch(self, rc, show_out="Sources:\n  main: snap [snapshot]\n", raise_oserror=False):
        def run(command, check):
            self.assertEqual(command[:3], ["aptly", "publish", "switch"])
            if raise_oserror:
                raise OSError("no aptly")
            return types.SimpleNamespace(returncode=rc)

        def show(args):
            return types.SimpleNamespace(returncode=0, stdout=show_out)

        def log(event, package, version, task_id):
            self.logged.append(event)
        return self.pa.consume_and_switch(TASK, self.approval, ["aptly", "publish", "switch", "resolute", "snap"],
                                          ["publish", "show", "resolute"], "snap", PACKAGE, VERSION,
                                          run=run, show=show, log=log)

    def outcome(self, used):
        return self.ar.read_used(used, TASK)[0]["outcome"]

    def test_success(self):
        used, sha, error = self.run_switch(0)
        self.assertIsNone(error)
        self.assertEqual(self.outcome(used), "published")
        self.assertEqual(self.ar.read_used(used, TASK)[1], sha)
        self.assertFalse(self.ar.path_for(TASK).exists())

    def test_failed_switch(self):
        used, sha, error = self.run_switch(3)
        self.assertEqual(error, (3, None))
        self.assertEqual(self.outcome(used), "failed(aptly rc 3)")
        self.assertIn("FAIL(3)", self.logged)
        self.assertFalse(self.ar.path_for(TASK).exists(), "a failed switch keeps the approval consumed")

    def test_failed_post_publication_check(self):
        used, sha, error = self.run_switch(0, show_out="Sources:\n  main: other [snapshot]\n")
        self.assertEqual(error[0], 2)
        self.assertIn("does not name the gated snapshot", error[1])
        self.assertEqual(self.outcome(used), "failed(post-publication check)")

    def test_aptly_cannot_start(self):
        used, sha, error = self.run_switch(0, raise_oserror=True)
        self.assertEqual(error[0], 2)
        self.assertEqual(self.outcome(used), "failed(start)")

    def test_consume_failure_stops_before_aptly(self):
        self.ar.write(dict(self.approval[0], known_gaps=["UNITY-20990101-009"]))  # rewritten under the publisher
        calls = []

        def run(command, check):
            calls.append(command)
        used, sha, error = self.pa.consume_and_switch(TASK, self.approval, ["aptly"], [], "snap", PACKAGE, VERSION,
                                                      run=run, show=lambda a: None, log=lambda *a: None)
        self.assertIsNone(used)
        self.assertIn("nothing was published", error[1])
        self.assertEqual(calls, [])


class PublishedAuthorizationCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tc = load("taskctl")
        self.ar = self.tc.approval_record
        self.ar.ROOT = Path(self.tmp.name) / "approvals"
        self.now = datetime(2099, 1, 1, tzinfo=timezone.utc)
        self.tc.AUTHORIZATION_REQUIRED_SINCE = "2098-01-01T00:00:00Z"
        rec = {"schema": 1, "kind": self.ar.KIND, "task_id": TASK, "approved_by": "C",
               "approved_at": self.ar.stamp(self.now), "not_after": self.ar.stamp(self.now + self.ar.WINDOW),
               "branch": "a/" + TASK, "gate_file": "rec/gate.json", "gate_sha256": "a" * 64, "gate_commit": "b" * 40,
               "package": PACKAGE, "candidate_version": VERSION, "source_repo": "packages/demo",
               "source_commit": "c" * 40, "source_tree_hash": "d" * 40, "snapshot": "snap",
               "distribution": "resolute", "prefix": ".", "build_manifest_sha256": "e" * 64,
               "evidence_manifest_sha256": "f" * 64,
               "artifacts": [{"file": "x.deb", "sha256": "1" * 64, "kind": "binary"}],
               "known_gaps": [], "first_publication": False, "may_reference": ""}
        self.ar.write(rec)
        _, sha, raw = self.ar.read(TASK, self.now)
        self.used, _ = self.ar.consume(TASK, raw, sha, "started", self.now)
        self.used_sha = self.ar.set_outcome(self.used, TASK, "published")
        self.record = {"task_id": TASK, "package": PACKAGE, "candidate_version": VERSION, "snapshot": "snap",
                       "distribution": "resolute", "prefix": ".", "published_at": "2099-01-01T00:10:00Z",
                       "authorization": {"file": str(Path(self.used).relative_to(self.ar.ROOT)),
                                         "sha256": self.used_sha, "approved_by": "C"}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid(self):
        self.tc.check_record_authorization(self.record, TASK)

    def test_record_before_the_cutover_needs_nothing(self):
        old = dict(self.record, published_at="2026-10-09T05:40:24Z")
        del old["authorization"]
        self.tc.check_record_authorization(old, TASK)

    def test_missing_authorization(self):
        rec = dict(self.record)
        del rec["authorization"]
        with self.assertRaisesRegex(ValueError, "no publication approval by C"):
            self.tc.check_record_authorization(rec, TASK)

    def test_sha_mismatch(self):
        rec = dict(self.record, authorization=dict(self.record["authorization"], sha256="0" * 64))
        with self.assertRaisesRegex(ValueError, "differs from the one the publish record names"):
            self.tc.check_record_authorization(rec, TASK)

    def test_outcome_not_published(self):
        new_sha = self.ar.set_outcome(self.used, TASK, "started")
        rec = dict(self.record, authorization=dict(self.record["authorization"], sha256=new_sha))
        with self.assertRaisesRegex(ValueError, "not published"):
            self.tc.check_record_authorization(rec, TASK)

    def test_used_copy_missing(self):
        Path(self.used).unlink()
        with self.assertRaisesRegex(ValueError, "cannot be read"):
            self.tc.check_record_authorization(self.record, TASK)

    def test_package_differs(self):
        rec = dict(self.record, package="other")
        with self.assertRaisesRegex(ValueError, "differ in package"):
            self.tc.check_record_authorization(rec, TASK)


if __name__ == "__main__":
    unittest.main()
