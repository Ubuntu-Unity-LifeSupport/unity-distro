#!/usr/bin/env python3
"""UNITY-20261008-019: a package task whose change shipped in another task's
build and publication reaches PUBLISHED with released_in (REVIEW ->
PUBLISHED, or BLOCKED -> PUBLISHED), then DONE; without released_in the
usual rules stay.

Each test copies taskctl.py into a scratch meta repository (scripts/, so its
repository is that one), imports the copy under its own name, points HOME and
TASKCTL_BOARD at a scratch home (board, evidence, publish records written
0444), and replaces the copy's confirm_live_publication. A scratch package
repository holds the change commits. Transitions run through main().
Run: python3 -m unittest discover -s scripts/tests
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
TASK = "UNITY-20990101-002"      # the task closed with released_in
OTHER = "UNITY-20990101-001"     # the releasing task
EARLIER = "UNITY-20980101-001"   # an earlier publication of the same package
VERSION = "1:1.0+unity5"


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


ARTIFACTS = [
    {"file": "demo_1.0+unity5.dsc", "sha256": sha("dsc"), "kind": "source", "package": "demo",
     "version": VERSION, "architecture": "source"},
    {"file": "demo-bin_1.0+unity5_amd64.deb", "sha256": sha("deb"), "kind": "binary", "package": "demo-bin",
     "version": VERSION, "architecture": "amd64"},
]


class ReleasedInTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.home = self.t / "home"
        self.coordinator = self.home / "coordinator"
        self.records = self.coordinator / "publish-records"
        (self.coordinator / "evidence").mkdir(parents=True)
        self.records.mkdir()
        self.board = self.coordinator / "TASKS.md"
        self.src = self.t / "src"
        self.make_package_repo()
        self.meta = self.t / "meta"
        (self.meta / "scripts").mkdir(parents=True)
        shutil.copy(SCRIPTS / "taskctl.py", self.meta / "scripts" / "taskctl.py")
        shutil.copy(SCRIPTS / "approval_record.py", self.meta / "scripts" / "approval_record.py")  # imported by taskctl
        spec = importlib.util.spec_from_file_location("taskctl_released_in_copy", self.meta / "scripts" / "taskctl.py")
        self.taskctl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.taskctl)
        self.live = None
        self.taskctl.confirm_live_publication = lambda record, distribution, prefix, run=None: self.live
        # These fixtures exercise released_in; the publication-approval check
        # (permission model phase 4) has its own tests and one integration
        # test below, so the cut-over is moved past the fixture dates here.
        self.taskctl.AUTHORIZATION_REQUIRED_SINCE = "2200-01-01T00:00:00Z"
        self.target_record = self.t / "target.txt"
        self.target_record.write_text("the change exercised on the published version\n")
        self.write_releasing_build()
        self.write_board()

    def tearDown(self):
        for path in self.records.glob("*"):
            if not path.is_symlink():
                os.chmod(path, 0o644)
        self.tmp.cleanup()

    # the package repository: c0 -> c1 (the task's change) -> c2 -> empty -> merge(side) -> shipped
    def git(self, *args, repo=None):
        return subprocess.run(["git", "-C", str(repo or self.src), *args], check=True, capture_output=True,
                              text=True).stdout.strip()

    def commit_file(self, name, text, message):
        (self.src / name).write_text(text)
        self.git("add", name)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def make_package_repo(self):
        self.src.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.c0 = self.commit_file("a", "a\n", "base (published earlier)")
        self.c1 = self.commit_file("b", "b\n", "the task's change")
        self.c2 = self.commit_file("c", "c\n", "another change")
        self.git("commit", "-q", "--allow-empty", "-m", "empty")
        self.empty = self.git("rev-parse", "HEAD")
        self.git("checkout", "-q", "-b", "side", self.c1)
        self.commit_file("d", "d\n", "side")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", "merge side", "side")
        self.merge = self.git("rev-parse", "HEAD")
        self.shipped = self.commit_file("e", "e\n", "release")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        self.git("checkout", "-q", "-b", "elsewhere", self.c0)
        self.unrelated = self.commit_file("z", "z\n", "never shipped")
        self.git("checkout", "-q", "main")

    def meta_file(self, rel, text):
        path = self.meta / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return rel

    def write_releasing_build(self, **gate_overrides):
        self.manifest = self.meta_file("docs/pub/build/manifest.json", json.dumps(
            {"schema": 1, "task_id": OTHER, "package": "demo", "candidate_version": VERSION,
             "source_commit": self.shipped, "artifacts": ARTIFACTS}))
        gate = {"schema": 1, "task_id": OTHER, "package": "demo", "candidate_version": VERSION,
                "task_state": "READY_TO_PUBLISH", "source_commit": self.shipped, "source_repo": str(self.src),
                "source_tree_hash": self.tree, "verification_result": "PASS", "version_safety": "SAFE",
                "publish": {"operation": "switch", "distribution": "resolute", "prefix": ".", "snapshot": "snap-001"},
                "build_manifest": {"file": self.manifest, "sha256": sha((self.meta / self.manifest).read_bytes())}}
        gate.update(gate_overrides)
        self.gate = self.meta_file("docs/pub/gate/release-gate.json", json.dumps(gate))
        self.record_sha = self.write_record(OTHER)

    def write_record(self, task_id, mode=0o444, **overrides):
        record = {"schema": 1, "task_id": task_id, "package": "demo", "candidate_version": VERSION,
                  "source_commit": self.shipped, "gate_file": self.gate,
                  "gate_sha256": sha((self.meta / self.gate).read_bytes()),
                  "snapshot": "snap-001", "distribution": "resolute", "prefix": ".",
                  "aptly_result": "PASS", "post_publish_check": "PASS",
                  "artifacts": [{k: a.get(k) for k in ("file", "sha256", "kind", "package", "version", "architecture")}
                                for a in ARTIFACTS],
                  "switch_time_version_check": {"result": "SAFE", "source_package": "demo",
                                                "candidate_source_version": VERSION, "checked_at": "2099-01-01T00:00:00Z"},
                  "switch_time_apt_view": {"tool": "apt_view.py", "mode": "full", "snapshot": {"name": "snap-001"}},
                  "published_at": "2099-01-01T12:00:00Z"}
        record.update(overrides)
        path = self.records / f"{task_id}.json"
        if path.exists():
            os.chmod(path, 0o644)
        path.write_text(json.dumps(record))
        os.chmod(path, mode)
        return sha(path.read_bytes())

    def write_earlier(self, commit, package="demo", **overrides):
        overrides.setdefault("published_at", "2098-01-01T12:00:00Z")
        return self.write_record(EARLIER, source_commit=commit, package=package, **overrides)

    def write_board(self, task_state="REVIEW", other_state="PUBLISHED", other=True):
        rows = [f"| {TASK} | demo: the covered change | B | target-desktop-2 | {task_state} | 2099-01-01 00:00Z | "
                f"2099-01-01 08:00Z | 2099-01-01 00:00Z | - |"]
        if other:
            rows.append(f"| {OTHER} | demo: the release | B | target-desktop-2 | {other_state} | 2099-01-01 00:00Z | "
                        f"2099-01-01 08:00Z | 2099-01-01 00:00Z | - |")
        self.board.write_text("# Tasks\n\n| ID | Title / package | Owner | Machine / resource | State | Claimed (UTC) | "
                              "Lease until (UTC) | Updated (UTC) | Evidence |\n|---|---|---|---|---|---|---|---|---|\n"
                              + "\n".join(rows) + "\n\n## Closed tasks\n")

    def evidence(self, **overrides):
        data = {"task_id": TASK, "task_kind": "package", "package_change": True, "package": "demo",
                "candidate_version": VERSION, "verification_record": "docs/card.md#verification",
                "verification_result": "PASS", "review_status": "REVIEWED", "target_verified": True,
                "target_verification_record": str(self.target_record), "terminal_evidence": "released with the release",
                "blocked_reason": "only to reach PUBLISHED", "resume_state": "PUBLISHED",
                "released_in": {"task_id": OTHER, "record_sha256": self.record_sha, "change_commits": [self.c1]}}
        for key, value in overrides.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        return data

    def released(self, **overrides):
        released = {"task_id": OTHER, "record_sha256": self.record_sha, "change_commits": [self.c1]}
        released.update(overrides)
        return released

    def transition(self, target, data):
        path = self.coordinator / "evidence" / f"{TASK}.json"
        path.write_text(json.dumps(data))
        argv = ["taskctl", "transition", TASK, target, "--actor", "B", "--evidence", str(path)]
        err = io.StringIO()
        env = {"HOME": str(self.home), "TASKCTL_BOARD": str(self.board), "ALERTS_FILE": str(self.t / "none.md")}
        with mock.patch.dict(os.environ, env), mock.patch.object(sys, "argv", argv), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = self.taskctl.main()
        return code, err.getvalue()

    def state(self):
        for line in self.board.read_text().splitlines():
            if line.startswith(f"| {TASK} |"):
                return line.split("|")[5].strip()

    def accepted(self, target, data):
        code, err = self.transition(target, data)
        self.assertEqual(0, code, err)
        self.assertEqual(target, self.state())

    def refused(self, target, data, fragment, state="REVIEW"):
        code, err = self.transition(target, data)
        self.assertEqual(2, code, f"accepted, expected a refusal with {fragment!r}")
        self.assertIn(fragment, err)
        self.assertEqual(state, self.state())

    def test_released_in_needs_the_releasing_tasks_approval_after_the_cutover(self):
        """Permission model phase 4: a releasing record dated after the cut-over
        must name C's consumed approval; the released task closes through it."""
        self.taskctl.AUTHORIZATION_REQUIRED_SINCE = "2000-01-01T00:00:00Z"
        ar = self.taskctl.approval_record
        ar.ROOT = self.coordinator / "publication-approvals"
        self.write_earlier(self.c0)
        self.refused("PUBLISHED", self.evidence(), "no publication approval by C")
        import datetime
        now = datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc)
        ar.write({"schema": 1, "kind": ar.KIND, "task_id": OTHER, "approved_by": "C",
                  "approved_at": ar.stamp(now), "not_after": ar.stamp(now + ar.WINDOW), "branch": "b/" + OTHER,
                  "gate_file": "rec/gate.json", "gate_sha256": "a" * 64, "gate_commit": "b" * 40,
                  "package": "demo", "candidate_version": VERSION, "source_repo": "packages/demo",
                  "source_commit": self.shipped, "source_tree_hash": "d" * 40, "snapshot": "snap-001",
                  "distribution": "resolute", "prefix": ".", "build_manifest_sha256": "e" * 64,
                  "evidence_manifest_sha256": "f" * 64,
                  "artifacts": [{"file": "x.deb", "sha256": "1" * 64, "kind": "binary"}],
                  "known_gaps": [], "first_publication": False, "may_reference": ""})
        _, sha_, raw = ar.read(OTHER, now)
        used, _ = ar.consume(OTHER, raw, sha_, "started", now)
        used_sha = ar.set_outcome(used, OTHER, "published")
        authorization = {"file": str(Path(used).relative_to(ar.ROOT)), "sha256": used_sha, "approved_by": "C"}
        self.record_sha = self.write_record(OTHER, authorization=authorization)
        self.accepted("PUBLISHED", self.evidence())

    # accepted
    def test_review_published_done(self):
        self.write_earlier(self.c0)
        self.accepted("PUBLISHED", self.evidence())
        self.accepted("DONE", self.evidence())

    def test_blocked_route_with_released_in(self):
        self.accepted("BLOCKED", self.evidence())
        self.accepted("PUBLISHED", self.evidence())

    def test_change_commit_equal_to_published_source(self):
        self.accepted("PUBLISHED", self.evidence(released_in=self.released(change_commits=[self.shipped])))

    def test_alternative_source_repository_with_the_right_tree(self):
        clone = self.t / "clone"
        subprocess.run(["git", "clone", "-q", str(self.src), str(clone)], check=True)
        self.write_releasing_build(source_repo=str(self.t / "gone"))
        self.accepted("PUBLISHED", self.evidence(released_in=self.released(source_repo=str(clone))))

    def test_matching_optional_fields(self):
        self.accepted("PUBLISHED", self.evidence(release_gate=self.gate, source_commit=self.shipped,
                                                 build_manifest=self.manifest))

    # the transition rules
    def test_review_published_without_released_in(self):
        self.refused("PUBLISHED", self.evidence(released_in=None), "REVIEW -> PUBLISHED needs released_in")

    def test_review_published_with_published_by(self):
        data = self.evidence(released_in=None, published_by={"task_id": OTHER, "record_sha256": self.record_sha})
        self.refused("PUBLISHED", data, "REVIEW -> PUBLISHED needs released_in")

    def test_blocked_route_without_anything(self):
        self.accepted("BLOCKED", self.evidence(released_in=None))
        self.refused("PUBLISHED", self.evidence(released_in=None), "publisher-created record is required",
                     state="BLOCKED")

    def test_ready_to_publish_with_released_in(self):
        self.write_board(task_state="READY_TO_PUBLISH")
        self.refused("PUBLISHED", self.evidence(), "published by its own record", state="READY_TO_PUBLISH")

    def test_review_done_with_released_in(self):
        self.refused("DONE", self.evidence(), "package tasks reach DONE only after PUBLISHED")

    def test_tool_kind(self):
        self.refused("PUBLISHED", self.evidence(task_kind="tool", package_change=False),
                     "belongs to a package task")

    def test_tool_kind_lock(self):
        lock = self.coordinator / "evidence" / f"{TASK}.kind"
        lock.write_text("tool\n")
        self.refused("PUBLISHED", self.evidence(), "held to task_kind=tool")

    def test_with_published_by(self):
        data = self.evidence(published_by={"task_id": OTHER, "record_sha256": self.record_sha})
        self.refused("PUBLISHED", data, "exclude each other")

    # released_in itself
    def test_own_task_id(self):
        self.refused("PUBLISHED", self.evidence(released_in=self.released(task_id=TASK)), "must name another task")

    def test_bad_shape(self):
        self.refused("PUBLISHED", self.evidence(released_in={"task_id": OTHER}), "released_in must be")
        self.refused("PUBLISHED", self.evidence(released_in=self.released(extra=1)), "released_in must be")

    def test_wrong_record_sha256(self):
        self.refused("PUBLISHED", self.evidence(released_in=self.released(record_sha256="0" * 64)),
                     "does not have the sha256")

    def test_writable_record(self):
        self.record_sha = self.write_record(OTHER, mode=0o644)
        self.refused("PUBLISHED", self.evidence(), "is writable")

    def test_symlinked_record(self):
        real = self.t / "real.json"
        shutil.copy(self.records / f"{OTHER}.json", real)
        os.chmod(self.records / f"{OTHER}.json", 0o644)
        (self.records / f"{OTHER}.json").unlink()
        (self.records / f"{OTHER}.json").symlink_to(real)
        self.refused("PUBLISHED", self.evidence(), "publisher-created record is required")

    def test_releasing_row_missing(self):
        self.write_board(other=False)
        self.refused("PUBLISHED", self.evidence(), "is not on the task board")

    def test_releasing_task_not_published(self):
        for other_state in ("READY_TO_PUBLISH", "BLOCKED"):
            self.write_board(other_state=other_state)
            self.refused("PUBLISHED", self.evidence(), f"is {other_state}, not PUBLISHED or DONE")

    def test_releasing_task_done(self):
        self.write_board(other_state="DONE")
        self.accepted("PUBLISHED", self.evidence())

    def test_other_package_or_version(self):
        self.refused("PUBLISHED", self.evidence(package="other"), "package differs")
        self.refused("PUBLISHED", self.evidence(candidate_version="1:1.0+unity4"), "candidate_version differs")

    def test_own_review_missing(self):
        self.refused("PUBLISHED", self.evidence(verification_result="FAIL"), "verification_result PASS")
        self.refused("PUBLISHED", self.evidence(verification_record=None), "verification_record")

    def test_independent_reproduction_required(self):
        self.refused("PUBLISHED", self.evidence(independent_reproduction_required=True),
                     "independent before/after reproduction")

    def test_differing_release_gate(self):
        self.refused("PUBLISHED", self.evidence(release_gate=self.gate + " (the other task's gate)"),
                     "name different gates")

    def test_differing_source_commit(self):
        self.refused("PUBLISHED", self.evidence(source_commit=self.c1), "must match gate field source_commit")

    def test_differing_build_manifest(self):
        self.refused("PUBLISHED", self.evidence(build_manifest="docs/own/manifest.json"), "different manifests")

    def test_gate_without_verifier_pass(self):
        self.write_releasing_build(verification_result="INCOMPLETE")
        self.refused("PUBLISHED", self.evidence(), "has no Verifier PASS")

    def test_short_empty_or_duplicate_commits(self):
        for commits in ([self.c1[:7]], [], [self.c1, self.c1]):
            self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=commits)),
                         "change_commits must be")

    def test_merge_commit(self):
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=[self.merge])),
                     "exactly one parent")

    def test_empty_commit(self):
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=[self.empty])),
                     "changes no file")

    def test_commit_not_in_published_source(self):
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=[self.unrelated])),
                     "is not in the published source commit")

    def test_unknown_commit(self):
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=["f" * 40])),
                     "is not a commit")

    def test_commit_shipped_earlier(self):
        self.write_earlier(self.c2)
        self.refused("PUBLISHED", self.evidence(), "already in an earlier publication")

    def test_earlier_record_of_another_package_is_ignored(self):
        self.write_earlier(self.c2, package="other")
        self.accepted("PUBLISHED", self.evidence())

    def test_later_record_is_ignored(self):
        self.write_record(EARLIER, source_commit=self.c2, published_at="2099-06-01T00:00:00Z")
        self.accepted("PUBLISHED", self.evidence())

    def test_earlier_record_with_unknown_commit(self):
        self.write_earlier("e" * 40)
        self.refused("PUBLISHED", self.evidence(), "is not a commit")

    def test_unreadable_earlier_record(self):
        path = self.records / f"{EARLIER}.json"
        path.write_text("{not json")
        os.chmod(path, 0o444)
        self.refused("PUBLISHED", self.evidence(), "is not JSON")

    def test_earlier_record_without_valid_time(self):
        self.write_earlier(self.c0, published_at="yesterday")
        self.refused("PUBLISHED", self.evidence(), "has no valid published_at")

    def test_other_files_in_the_records_directory(self):
        (self.records / f"{EARLIER}-apt-view.json").write_text("{not json")
        (self.records / f"{EARLIER}.lock").write_text("")
        self.accepted("PUBLISHED", self.evidence())

    def test_missing_source_repository(self):
        self.write_releasing_build(source_repo=str(self.t / "gone"))
        self.refused("PUBLISHED", self.evidence(), "is not available")

    def test_gate_tree_differs_from_the_repository(self):
        # A repository holding the published commit has its tree (hashes); the
        # gate's tree must agree with it.
        self.write_releasing_build(source_tree_hash="1" * 40)
        self.refused("PUBLISHED", self.evidence(), "not the gate's source_tree_hash")

    # git's history overrides must not count: only object hashes do
    def clone(self, name="clone"):
        path = self.t / name
        subprocess.run(["git", "clone", "-q", str(self.src), str(path)], check=True)
        return path

    def parentless_copy(self, repo, commit):
        """A new root commit with commit's tree, made in repo."""
        tree = self.git("rev-parse", f"{commit}^{{tree}}", repo=repo)
        return self.git("commit-tree", tree, "-m", "same tree, other history", repo=repo)

    def test_replace_ref_in_the_evidence_repository(self):
        clone = self.clone()
        fake = self.git("commit-tree", self.tree, "-p", self.unrelated, "-m", "fake release", repo=clone)
        self.git("replace", self.shipped, fake, repo=clone)
        self.write_releasing_build(source_repo=str(self.t / "gone"))
        data = self.evidence(released_in=self.released(source_repo=str(clone), change_commits=[self.unrelated]))
        self.refused("PUBLISHED", data, "is not in the published source commit")

    def test_replace_ref_in_the_gate_repository(self):
        fake = self.git("commit-tree", self.tree, "-p", self.unrelated, "-m", "fake release")
        self.git("replace", self.shipped, fake)
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=[self.unrelated])),
                     "is not in the published source commit")

    def test_replace_ref_hiding_an_earlier_publication(self):
        self.write_earlier(self.c2)
        self.git("replace", self.c2, self.parentless_copy(self.src, self.c2))
        self.refused("PUBLISHED", self.evidence(), "already in an earlier publication")

    def test_grafts_file(self):
        (self.src / ".git" / "info").mkdir(exist_ok=True)
        (self.src / ".git" / "info" / "grafts").write_text(f"{self.shipped} {self.merge} {self.unrelated}\n")
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=[self.unrelated])),
                     "is not in the published source commit")

    def test_grafts_from_the_environment(self):
        grafts = self.t / "grafts"
        grafts.write_text(f"{self.shipped} {self.merge} {self.unrelated}\n")
        with mock.patch.dict(os.environ, {"GIT_GRAFT_FILE": str(grafts)}):
            self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=[self.unrelated])),
                         "is not in the published source commit")

    def test_shallow_repository(self):
        self.write_earlier(self.c2)
        (self.src / ".git" / "shallow").write_text(self.c2 + "\n")
        self.refused("PUBLISHED", self.evidence(), "is shallow")

    # an object stored under a real commit's id must hash to that id
    def forged_object(self, commit, new_parent):
        """zlib bytes of a commit object like `commit` but with another parent (it hashes to another id)."""
        import zlib
        body = subprocess.run(["git", "-C", str(self.src), "cat-file", "commit", commit], check=True,
                              capture_output=True).stdout
        lines = body.split(b"\n")
        lines = [b"parent " + new_parent.encode() if line.startswith(b"parent ") else line for line in lines]
        body = b"\n".join(lines)
        return zlib.compress(b"commit %d\0" % len(body) + body)

    def put_loose(self, objects, commit, data):
        path = objects / commit[:2] / commit[2:]
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            os.chmod(path, 0o644)
        path.write_bytes(data)

    def test_forged_intermediate_commit_loose(self):
        self.put_loose(self.src / ".git" / "objects", self.c2, self.forged_object(self.c2, self.unrelated))
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=[self.unrelated])),
                     "does not hash to its id")

    def test_forged_intermediate_commit_hiding_an_earlier_publication(self):
        self.write_earlier(self.empty)
        self.put_loose(self.src / ".git" / "objects", self.c2, self.forged_object(self.c2, self.c0))
        self.refused("PUBLISHED", self.evidence(), "does not hash to its id")

    def test_forged_intermediate_commit_packed(self):
        self.put_loose(self.src / ".git" / "objects", self.c2, self.forged_object(self.c2, self.unrelated))
        packed = subprocess.run(["git", "-C", str(self.src), "repack", "-a", "-d", "-q"], capture_output=True)
        if packed.returncode:
            self.skipTest("git refused to pack the forged object")
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=[self.unrelated])),
                     "does not hash to its id")

    def test_forged_intermediate_commit_behind_alternates(self):
        copy = self.t / "copy"
        shutil.copytree(self.src, copy, symlinks=True)
        real = copy / ".git" / "objects" / self.c2[:2] / self.c2[2:]
        os.chmod(real, 0o644)
        real.unlink()
        store = self.t / "store" / "objects"
        self.put_loose(store, self.c2, self.forged_object(self.c2, self.unrelated))
        (copy / ".git" / "objects" / "info").mkdir(exist_ok=True)
        (copy / ".git" / "objects" / "info" / "alternates").write_text(str(store) + "\n")
        self.write_releasing_build(source_repo=str(self.t / "gone"))
        data = self.evidence(released_in=self.released(source_repo=str(copy), change_commits=[self.unrelated]))
        self.refused("PUBLISHED", data, "does not hash to its id")

    # git must not run anything the repository's config names
    def marker_program(self, name):
        marker = self.t / f"{name}.ran"
        program = self.t / f"{name}.sh"
        program.write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n")
        program.chmod(0o755)
        return program, marker

    def test_fsmonitor_does_not_run(self):
        program, marker = self.marker_program("fsmonitor")
        self.git("config", "core.fsmonitor", str(program))
        self.accepted("PUBLISHED", self.evidence())
        self.assertFalse(marker.exists())

    def test_partial_clone_is_refused_and_fetches_nothing(self):
        program, marker = self.marker_program("uploadpack")
        self.git("remote", "add", "origin", str(self.t / "nowhere"))
        self.git("config", "remote.origin.promisor", "true")
        self.git("config", "remote.origin.uploadpack", str(program))
        self.git("config", "extensions.partialClone", "origin")
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=["f" * 40])),
                     "is a partial clone")
        self.assertFalse(marker.exists())

    def test_missing_object_fetches_nothing(self):
        program, marker = self.marker_program("uploadpack2")
        self.git("remote", "add", "origin", str(self.t / "nowhere"))
        self.git("config", "remote.origin.uploadpack", str(program))
        self.refused("PUBLISHED", self.evidence(released_in=self.released(change_commits=["f" * 40])),
                     "is not a commit")
        self.assertFalse(marker.exists())

    # commits are read as git reads them
    def literal_commit(self, text):
        return subprocess.run(["git", "-C", str(self.src), "hash-object", "-t", "commit", "-w", "--literally",
                               "--stdin"], input=text.encode(), check=True, capture_output=True).stdout.decode().strip()

    def test_extra_parent_after_committer(self):
        text = (f"tree {self.tree}\nparent {self.c2}\nauthor t <t@example.invalid> 0 +0000\n"
                f"committer t <t@example.invalid> 0 +0000\nparent {self.unrelated}\n\nodd\n")
        history = self.taskctl.VerifiedHistory(str(self.src))
        try:
            with self.assertRaises(ValueError) as caught:
                history.commit(self.literal_commit(text))
        finally:
            history.close()
        self.assertIn("not a well-formed commit", str(caught.exception))

    def test_parent_before_tree(self):
        text = (f"parent {self.c2}\ntree {self.tree}\nauthor t <t@example.invalid> 0 +0000\n"
                f"committer t <t@example.invalid> 0 +0000\n\nodd\n")
        history = self.taskctl.VerifiedHistory(str(self.src))
        try:
            with self.assertRaises(ValueError) as caught:
                history.commit(self.literal_commit(text))
        finally:
            history.close()
        self.assertIn("not a well-formed commit", str(caught.exception))

    # taskctl holds the board lock: a blocked read in the repository must not hang it
    def test_named_pipe_as_shallow_file(self):
        self.taskctl.GIT_TIMEOUT = 2
        os.mkfifo(self.src / ".git" / "shallow")
        self.refused("PUBLISHED", self.evidence(), "did not finish")

    def test_named_pipe_as_loose_object(self):
        self.taskctl.GIT_TIMEOUT = 2
        # the merge commit: every path from the published commit passes it
        path = self.src / ".git" / "objects" / self.merge[:2] / self.merge[2:]
        os.chmod(path, 0o644)
        path.unlink()
        os.mkfifo(path)
        self.refused("PUBLISHED", self.evidence(), "is not a commit")

    def test_own_review_status_missing(self):
        self.refused("PUBLISHED", self.evidence(review_status="PENDING"), "review_status")

    def test_earlier_record_at_the_same_time_counts(self):
        self.write_earlier(self.c2, published_at="2099-01-01T12:00:00Z")
        self.refused("PUBLISHED", self.evidence(), "already in an earlier publication")

    def test_relative_source_repository(self):
        self.refused("PUBLISHED", self.evidence(released_in=self.released(source_repo="src")), "absolute path")

    def test_live_check_failing(self):
        self.live = "the live snapshot does not carry the record's artifacts"
        self.refused("PUBLISHED", self.evidence(), "does not carry the record's artifacts")

    def test_no_target_record(self):
        self.refused("PUBLISHED", self.evidence(target_verification_record=None),
                     "requires evidence fields: target_verification_record")
        self.refused("PUBLISHED", self.evidence(target_verified=False), "target_verified=true")


if __name__ == "__main__":
    unittest.main()
