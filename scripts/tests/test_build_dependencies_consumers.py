#!/usr/bin/env python3
"""UNITY-20260929-014: create_release_gate.py and publish_aptly.py, run for
real, refuse a manifest whose build_dependencies fail the check, and treat a
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

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
TASK, PACKAGE, VERSION, SERIES = "UNITY-20990101-001", "demo", "1.0+unity1", "resolute"
DEP_NAME = "libdemo-dev_2.0+unity1_amd64.deb"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ConsumersEndToEndTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root, self.home, self.pool = base / "repo", base / "home", base / "pool"
        bindir = base / "bin"
        bindir.mkdir()
        self.aptly_log = base / "aptly-calls.log"
        (bindir / "aptly").write_text(f"#!/bin/sh\necho \"$*\" >> '{self.aptly_log}'\nexit 1\n")
        (bindir / "aptly").chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=f"{bindir}:{os.environ['PATH']}",
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
                        GIT_CONFIG_NOSYSTEM="1")
        self.assertEqual(shutil.which("aptly", path=self.env["PATH"]), str(bindir / "aptly"))

        # scripts/, with the pool redirected in the copy only
        (self.root / "scripts").mkdir(parents=True)
        for script in SCRIPTS.glob("*.py"):
            shutil.copy2(script, self.root / "scripts" / script.name)
        module = self.root / "scripts" / "build_dependencies.py"
        text = module.read_text()
        original = 'POOL_ROOT = Path("/srv/aptly/public/pool")'
        self.assertIn(original, text)
        module.write_text(text.replace(original, f"POOL_ROOT = Path({str(self.pool)!r})"))

        # the package checkout, with a remote-tracking ref
        self.pkg = self.root / "packages" / PACKAGE
        self.pkg.mkdir(parents=True)
        self.git(self.pkg, "init", "-q")
        (self.pkg / "README").write_text("demo\n")
        self.git(self.pkg, "add", "README")
        self.git(self.pkg, "commit", "-qm", "demo")
        self.commit = self.git(self.pkg, "rev-parse", "HEAD")
        self.tree = self.git(self.pkg, "rev-parse", "HEAD^{tree}")
        self.git(self.pkg, "update-ref", "refs/remotes/origin/main", self.commit)

        # the gate repository and its "remote"
        self.remote = base / "remote.git"
        self.git(base, "init", "-q", "--bare", str(self.remote))
        self.git(self.root, "init", "-q")
        (self.root / ".gitignore").write_text("/packages/\n*.deb\n__pycache__/\n")
        self.git(self.root, "remote", "add", "origin", str(self.remote))

        # the build: one artifact, one extra build dependency present in the pool
        self.build = self.root / "rec" / "build"
        (self.build / "build-dependencies").mkdir(parents=True)
        self.make_deb(self.build / "demo_1.0+unity1_amd64.deb", PACKAGE, VERSION, PACKAGE)
        (self.build / "build.log").write_text("log\n")
        # UNITY-20261008-003: the build's .buildinfo is committed with its manifest
        self.buildinfo = self.build / "demo_1.0+unity1_amd64.buildinfo"
        self.buildinfo.write_text(f"Format: 1.0\nSource: {PACKAGE}\nBinary: {PACKAGE}\nArchitecture: amd64\n"
                                  f"Version: {VERSION}\nBuild-Architecture: amd64\n"
                                  "Installed-Build-Depends:\n base-files (= 14ubuntu6.2)\n")
        self.git(self.root, "add", str(self.buildinfo.relative_to(self.root)))
        self.git(self.root, "commit", "-qm", "buildinfo")
        pooled = self.pool / "main" / "libd" / "libdemo" / DEP_NAME
        self.make_deb(pooled, "libdemo-dev", "2.0+unity1", "libdemo")
        shutil.copy2(pooled, self.build / "build-dependencies" / DEP_NAME)
        self.entry = {"file": f"build-dependencies/{DEP_NAME}", "sha256": sha(pooled), "size": pooled.stat().st_size,
                      "package": "libdemo-dev", "version": "2.0+unity1", "architecture": "amd64", "source": "libdemo",
                      "in_our_repository_pool": True, "pool_path": str(pooled)}
        (self.home / "coordinator").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, repo, *args):
        return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                              env=self.env).stdout.strip()

    def make_deb(self, path, package, version, source):
        tree = path.parent / f".t-{path.name}"
        (tree / "DEBIAN").mkdir(parents=True)
        (tree / "DEBIAN" / "control").write_text(
            f"Package: {package}\nVersion: {version}\nArchitecture: amd64\nSource: {source}\n"
            "Maintainer: t <t@example.com>\nDescription: t\n")
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(tree), str(path)],
                       check=True, capture_output=True)
        shutil.rmtree(tree)

    def write_manifest(self, entries):
        manifest = {"schema": 1, "task_id": TASK, "package": PACKAGE, "candidate_version": VERSION,
                    "target_series": SERIES, "source_repo": f"packages/{PACKAGE}", "source_commit": self.commit,
                    "source_tree_hash": self.tree, "result": "PASS",
                    "build_started": "2099-01-01T00:00:00+00:00", "build_finished": "2099-01-01T00:01:00+00:00",
                    "log": {"file": "build.log", "sha256": sha(self.build / "build.log")},
                    "artifacts": [{"file": "demo_1.0+unity1_amd64.deb", "kind": "binary", "package": PACKAGE,
                                   "version": VERSION, "architecture": "amd64",
                                   "sha256": sha(self.build / "demo_1.0+unity1_amd64.deb")},
                                  {"file": self.buildinfo.name, "kind": "buildinfo", "package": PACKAGE,
                                   "version": VERSION, "architecture": "amd64", "sha256": sha(self.buildinfo)}]}
        if entries is not None:
            manifest["build_dependencies"] = entries
        manifest.update(getattr(self, "manifest_extra", {}))  # UNITY-20260929-020
        path = self.build / "manifest.json"
        path.write_text(json.dumps(manifest, indent=1))
        return path

    def board(self, state, evidence="-"):
        (self.home / "coordinator" / "TASKS.md").write_text(
            "| ID | Title | Owner | Machine | State | Claimed | Heartbeat | Updated | Evidence |\n"
            f"| {TASK} | demo | A | target | {state} | x | x | x | {evidence} |\n")

    def run_script(self, *argv):
        result = subprocess.run([sys.executable, *argv], cwd=self.root, env=self.env,
                                capture_output=True, text=True, timeout=120)
        self.assertFalse(self.aptly_log.exists(), f"aptly was called: {self.aptly_log.read_text() if self.aptly_log.exists() else ''}")
        return result

    def create_release_gate(self, entries):
        """Stops after the check at its next step: empty --snapshot/--distribution."""
        manifest = self.write_manifest(entries)
        record = self.root / "rec" / "record.json"
        record.write_text(json.dumps({"task_id": TASK, "package": PACKAGE, "target_series": SERIES,
                                      "candidate_version": VERSION, "source_commit": self.commit,
                                      "verification_result": "PASS", "peer_notice": "ACK",
                                      "patch_and_decision_docs": "docs", "source_provenance": "PUSHED",
                                      **getattr(self, "record_extra", {})}))
        self.board("REVIEW")
        return self.run_script("scripts/create_release_gate.py", "--record", str(record), "--build-manifest",
                               str(manifest), "--snapshot", "", "--distribution", "",
                               "--output", str(self.root / "rec" / "gate-out.json"))

    def publish(self, entries):
        """Stops after the check at its next step: the gate has no evidence_manifest."""
        manifest = self.write_manifest(entries)
        gate = self.root / "rec" / "gate.json"
        extra = getattr(self, "gate_extra", {})
        if callable(extra):
            extra = extra(json.loads(manifest.read_text()))
        gate.write_text(json.dumps({**extra, 
            "schema": 1, "task_id": TASK, "package": PACKAGE, "candidate_version": VERSION, "target_series": SERIES,
            "task_state": "READY_TO_PUBLISH", "source_tree": "CLEAN", "target_series_build": "PASS",
            "version_safety": "SAFE", "patch_and_decision_docs": "COMPLETE", "source_provenance": "PUSHED",
            "verification_result": "PASS", "peer_notice": "ACK", "source_repo": f"packages/{PACKAGE}",
            "source_commit": self.commit, "source_tree_hash": self.tree, "source_remote_ref": "origin/main",
            "build_manifest": {"file": str(manifest.relative_to(self.root)), "sha256": sha(manifest)}}))
        self.git(self.root, "add", "-A")
        self.git(self.root, "commit", "-qm", "gate")
        if getattr(self, "after_gate", None):  # UNITY-20260929-020: change a file after the gate
            self.after_gate()
            self.git(self.root, "add", "-A")
            self.git(self.root, "commit", "-qm", "after the gate")
        self.git(self.root, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.git(self.root, "fetch", "-q", "origin")
        evidence = self.home / "evidence.json"
        evidence.write_text(json.dumps({"task_id": TASK, "package": PACKAGE, "candidate_version": VERSION,
                                        "source_commit": self.commit, "version_safety": "SAFE",
                                        "release_gate": "rec/gate.json"}))
        self.board("READY_TO_PUBLISH", str(evidence))
        return self.run_script("scripts/publish_aptly.py", "--gate", str(gate))

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
