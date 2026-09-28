#!/usr/bin/env python3
"""Regression tests for the task kinds of scripts/taskctl.py (UNITY-20260928-005).

Every test drives the real taskctl.py on a temporary board (TASKCTL_BOARD)
with fixture evidence files; the kind lock lands in <board dir>/evidence/.
Run: python3 -m unittest discover -s scripts/tests
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(os.environ.get("TASKCTL", Path(__file__).resolve().parents[1] / "taskctl.py"))
TID = "UNITY-20990101-001"

DEFECT_CARD = {
    "reproduction": "tools/repro.sh", "reproduction_result": "PASS",
    "existing_fix_result": "NOT_FIXED", "issue_search_result": "NOT_FOUND",
    "root_cause": "a real cause", "root_cause_mechanism": "a real mechanism",
    "root_cause_evidence": "runs/x.txt", "invariant": "an invariant",
    "chosen_approach": "the fix", "correct_layer": "this function",
    "architectural_task": False, "design_challenger_required": False,
}
PLAN = {"scope": "what is done", "chosen_approach": "how", "correct_layer": "where",
        "architectural_task": False, "design_challenger_required": False}
AUTH = {"approved_by": "May", "reference": "~/coordinator/PENDING-MAY.md 2099-01-01", "scope": "create repositories"}
REVIEW_PASS = {"verification_record": "review.md", "verification_result": "PASS",
               "review_status": "INDEPENDENTLY_REPRODUCED"}


class TaskctlKindsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.board = self.base / "TASKS.md"
        self.lock = self.base / "evidence" / f"{TID}.kind"

    def tearDown(self):
        self.tmp.cleanup()

    def make_board(self, state):
        self.board.write_text("\n".join([
            "# test board", "",
            "| ID | Title | Owner | Machine | State | Claimed | Lease | Updated | Evidence |",
            "|---|---|---|---|---|---|---|---|---|",
            f"| {TID} | test | A | target-desktop | {state} | 2099-01-01 00:00Z | 2099-01-01 08:00Z | 2099-01-01 00:00Z | - |",
            "", "## Closed tasks", "",
            "| ID | Title / package | Owner | Machine / resource | State | Claimed (UTC) | Lease until (UTC) | Updated (UTC) | Evidence |",
            "|---|---|---|---|---|---|---|---|---|", ""]))

    def state(self):
        for line in self.board.read_text().splitlines():
            if line.startswith(f"| {TID} |"):
                return [c.strip() for c in line.strip().strip("|").split("|")][4]

    def go(self, target, name="e.json", **evidence):
        path = self.base / name
        path.write_text(json.dumps(dict({"task_id": TID}, **evidence)))
        result = subprocess.run([sys.executable, str(SCRIPT), "transition", TID, target, "--actor", "A",
                                 "--evidence", str(path)],
                                env=dict(os.environ, TASKCTL_BOARD=str(self.board)), capture_output=True, text=True)
        return result.returncode, result.stderr

    def assert_ok(self, rc_err, state):
        self.assertEqual(rc_err[0], 0, rc_err[1])
        self.assertEqual(self.state(), state)

    def assert_refused(self, rc_err, fragment, state):
        self.assertNotEqual(rc_err[0], 0)
        self.assertIn(fragment, rc_err[1])
        self.assertEqual(self.state(), state)

    # DONE paths per kind

    def test_tool_done_only_from_review_with_pass(self):
        self.make_board("REVIEW")
        self.assert_ok(self.go("DONE", task_kind="tool", terminal_evidence="merged", **REVIEW_PASS), "DONE")

    def test_tool_review_done_refused_without_pass(self):
        for result in ("FAIL", "INCOMPLETE"):
            with self.subTest(result=result):
                self.tearDown(); self.setUp(); self.make_board("REVIEW")
                ev = dict(REVIEW_PASS, verification_result=result)
                self.assert_refused(self.go("DONE", task_kind="tool", terminal_evidence="x", **ev),
                                    "verification_result=PASS", "REVIEW")

    def test_tool_verifying_done_refused(self):
        """Reproduced gap 3: tool code may no longer skip the Verifier."""
        self.make_board("VERIFYING")
        self.assert_refused(self.go("DONE", task_kind="tool", package_change=False, validation_record="t",
                                    terminal_evidence="x"), "only from REVIEW", "VERIFYING")

    def test_documentation_done_from_verifying_and_review(self):
        self.make_board("VERIFYING")
        self.assert_ok(self.go("DONE", task_kind="documentation", validation_record="read",
                               terminal_evidence="x"), "DONE")
        self.tearDown(); self.setUp(); self.make_board("REVIEW")
        self.assert_ok(self.go("DONE", task_kind="documentation", terminal_evidence="x", **REVIEW_PASS), "DONE")

    def test_operation_done_from_verifying(self):
        self.make_board("VERIFYING")
        self.assert_ok(self.go("DONE", task_kind="operation", validation_record="ls-remote",
                               terminal_evidence="x"), "DONE")

    def test_package_done_refused_from_review_and_verifying(self):
        for state in ("REVIEW", "VERIFYING"):
            with self.subTest(state=state):
                self.tearDown(); self.setUp(); self.make_board(state)
                self.assert_refused(self.go("DONE", task_kind="package", terminal_evidence="x", **REVIEW_PASS),
                                    "only after PUBLISHED", state)

    def test_legacy_package_refused_on_review_done(self):
        """package_change=true without task_kind is a package (fail-safe)."""
        self.make_board("REVIEW")
        self.assert_refused(self.go("DONE", package_change=True, terminal_evidence="x", **REVIEW_PASS),
                            "only after PUBLISHED", "REVIEW")

    def test_legacy_package_done_from_published(self):
        self.make_board("PUBLISHED")
        self.assert_ok(self.go("DONE", package_change=True, terminal_evidence="x"), "DONE")

    # kind resolution

    def test_missing_kind_refused_from_ready_for_fix(self):
        self.make_board("INVESTIGATING")
        self.assert_refused(self.go("READY_FOR_FIX", package_change=False, **DEFECT_CARD),
                            "requires task_kind", "INVESTIGATING")

    def test_non_bool_and_mismatched_package_change(self):
        cases = [({"task_kind": "tool", "package_change": "no"}, "true or false"),
                 ({"task_kind": "tool", "package_change": True}, "contradicts"),
                 ({"task_kind": "package", "package_change": False}, "contradicts"),
                 ({"task_kind": "script"}, "task_kind must be one of")]
        for evidence, fragment in cases:
            with self.subTest(evidence=evidence):
                self.tearDown(); self.setUp(); self.make_board("INVESTIGATING")
                self.assert_refused(self.go("READY_FOR_FIX", **dict(DEFECT_CARD, **evidence)), fragment, "INVESTIGATING")

    def test_package_markers_force_package(self):
        for marker in ("build_manifest", "release_gate", "candidate_version", "version_safety"):
            with self.subTest(marker=marker):
                self.tearDown(); self.setUp(); self.make_board("REVIEW")
                self.assert_refused(self.go("DONE", task_kind="tool", terminal_evidence="x",
                                            **dict(REVIEW_PASS, **{marker: "x"})),
                                    "belongs to a package task", "REVIEW")

    def test_non_package_cannot_publish(self):
        self.make_board("REVIEW")
        self.assert_refused(self.go("READY_TO_PUBLISH", task_kind="tool", **REVIEW_PASS),
                            "only package tasks are published", "REVIEW")

    # the kind lock

    def test_kind_locked_at_ready_for_fix(self):
        self.make_board("INVESTIGATING")
        self.assert_ok(self.go("READY_FOR_FIX", task_kind="tool", **DEFECT_CARD), "READY_FOR_FIX")
        self.assertEqual(self.lock.read_text().strip(), "tool")
        self.assert_refused(self.go("IMPLEMENTING", name="other.json", task_kind="documentation",
                                    implementation_plan="p"), "held to task_kind=tool", "READY_FOR_FIX")
        self.assert_ok(self.go("IMPLEMENTING", implementation_plan="p"), "IMPLEMENTING")  # kind from the lock

    def test_seeded_legacy_package_cannot_be_relabelled(self):
        """A lock written at deployment (tools/seed-kind-locks.py) holds an
        open legacy package task before its first transition."""
        self.make_board("REVIEW")
        self.lock.parent.mkdir(parents=True)
        self.lock.write_text("package\n")
        self.assert_refused(self.go("DONE", task_kind="tool", terminal_evidence="x", **REVIEW_PASS),
                            "held to task_kind=package", "REVIEW")
        self.assert_refused(self.go("DONE", package_change=False, terminal_evidence="x", **REVIEW_PASS),
                            "package_change contradicts", "REVIEW")

    def test_invalid_lock_contents_refused(self):
        """Verifier finding (UNITY-20260928-005 review 1): a lock that does not
        hold exactly one kind must never stand in for a kind."""
        for content in ("", "garbage", "Package", "package\nxx", "tool tool"):
            with self.subTest(content=content):
                self.tearDown(); self.setUp(); self.make_board("VERIFYING")
                self.lock.parent.mkdir(parents=True)
                self.lock.write_text(content)
                self.assert_refused(self.go("DONE", validation_record="v", terminal_evidence="x"),
                                    "repair it before any transition", "VERIFYING")

    def test_lock_with_surrounding_whitespace_accepted(self):
        self.make_board("REVIEW")
        self.lock.parent.mkdir(parents=True)
        self.lock.write_text("  tool \n\n")
        self.assert_ok(self.go("DONE", terminal_evidence="x", **REVIEW_PASS), "DONE")

    def test_lock_written_whole(self):
        self.make_board("INVESTIGATING")
        self.assert_ok(self.go("READY_FOR_FIX", task_kind="documentation", **PLAN), "READY_FOR_FIX")
        self.assertEqual(self.lock.read_text(), "documentation\n")
        self.assertEqual(sorted(p.name for p in self.lock.parent.iterdir()), [self.lock.name])

    # READY_FOR_FIX per kind

    def test_operation_and_documentation_ready_without_defect_fields(self):
        self.make_board("INVESTIGATING")
        self.assert_ok(self.go("READY_FOR_FIX", task_kind="operation", existing_state_check="none there",
                               authorization=AUTH, **PLAN), "READY_FOR_FIX")
        self.tearDown(); self.setUp(); self.make_board("INVESTIGATING")
        self.assert_ok(self.go("READY_FOR_FIX", task_kind="documentation", **PLAN), "READY_FOR_FIX")

    def test_operation_authorization_required(self):
        cases = [({}, "authorization"),
                 ({"authorization": "May said so"}, "authorization"),
                 ({"authorization": dict(AUTH, approved_by="B")}, "approved_by"),
                 ({"authorization": dict(AUTH, reference="TBD")}, "reference")]
        for extra, fragment in cases:
            with self.subTest(extra=extra):
                self.tearDown(); self.setUp(); self.make_board("INVESTIGATING")
                self.assert_refused(self.go("READY_FOR_FIX", task_kind="operation", existing_state_check="x",
                                            **dict(PLAN, **extra)), fragment, "INVESTIGATING")

    def test_tool_still_needs_defect_card(self):
        self.make_board("INVESTIGATING")
        self.assert_refused(self.go("READY_FOR_FIX", task_kind="tool", **PLAN), "reproduction", "INVESTIGATING")

    # VERIFYING per kind

    def test_verifying_requirements(self):
        cases = [("tool", {"validation_record": "v"}, "regression_test"),
                 ("tool", {"regression_test": "t"}, "validation_record"),
                 ("operation", {}, "validation_record"),
                 ("package", {"regression_test": "t"}, "build_manifest")]
        for kind, evidence, fragment in cases:
            with self.subTest(kind=kind, evidence=evidence):
                self.tearDown(); self.setUp(); self.make_board("IMPLEMENTING")
                self.assert_refused(self.go("VERIFYING", task_kind=kind, **evidence), fragment, "IMPLEMENTING")

    # BLOCKED

    def test_blocked_resume_into_review_then_done_by_kind(self):
        self.make_board("BLOCKED")
        self.assert_ok(self.go("REVIEW", task_kind="tool", resume_state="REVIEW", **REVIEW_PASS), "REVIEW")
        self.assert_ok(self.go("DONE", task_kind="tool", terminal_evidence="x", **REVIEW_PASS), "DONE")

    def test_blocked_cannot_resume_into_done(self):
        self.make_board("BLOCKED")
        self.assert_refused(self.go("DONE", task_kind="documentation", resume_state="DONE", terminal_evidence="x"),
                            "not allowed", "BLOCKED")


if __name__ == "__main__":
    unittest.main()
