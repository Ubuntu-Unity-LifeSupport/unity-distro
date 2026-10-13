#!/usr/bin/env python3
"""End-to-end harness for create_release_gate.py, publish_aptly.py and
taskctl.py, run for real in a temporary copy of the repository (extracted from
test_build_dependencies_consumers.py, UNITY-20260929-014, for the permission
model phase 4).

Each run happens in a temporary copy of the repository: scripts/ copied with
build_dependencies.POOL_ROOT and the live public tree pointed at temporary
trees, a git repository with a local "remote", a package checkout under
packages/, and a fake HOME holding the task board and the task evidence.
Safety: PATH starts with a fake `aptly` that only records its arguments and
exits 1, the harness checks that `aptly` resolves to it, and every case must
leave its log empty - no case gets as far as calling aptly.
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


class PublishHarness(unittest.TestCase):
    live_sources = (PACKAGE,)  # source names the fake live publication lists

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root, self.home, self.pool = base / "repo", base / "home", base / "pool"
        self.public = base / "public"
        bindir = base / "bin"
        bindir.mkdir()
        self.aptly_log = base / "aptly-calls.log"
        (bindir / "aptly").write_text(f"#!/bin/sh\necho \"$*\" >> '{self.aptly_log}'\nexit 1\n")
        (bindir / "aptly").chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=f"{bindir}:{os.environ['PATH']}",
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
                        GIT_CONFIG_NOSYSTEM="1", TASKCTL_BOARD=str(self.home / "coordinator" / "TASKS.md"))
        self.assertEqual(shutil.which("aptly", path=self.env["PATH"]), str(bindir / "aptly"))

        # scripts/ and signer/ (the publisher imports the signer client, phase 5), with the
        # pool and the live public tree redirected in the copy only
        (self.root / "scripts").mkdir(parents=True)
        for script in SCRIPTS.glob("*.py"):
            shutil.copy2(script, self.root / "scripts" / script.name)
        (self.root / "signer").mkdir()
        for module in (SCRIPTS.parent / "signer").glob("*.py"):
            shutil.copy2(module, self.root / "signer" / module.name)
        shutil.copy2(SCRIPTS.parent / "signer" / "release-template.json", self.root / "signer" / "release-template.json")
        self.redirect(self.root / "scripts" / "build_dependencies.py",
                      'POOL_ROOT = Path("/srv/aptly/public/pool")', f"POOL_ROOT = Path({str(self.pool)!r})")
        for name in ("publish_aptly.py", "taskctl.py"):
            self.redirect(self.root / "scripts" / name,
                          'LIVE_PUBLIC = Path("/srv/aptly/public")', f"LIVE_PUBLIC = Path({str(self.public)!r})")
        self.write_live_publication(self.live_sources)

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

    def redirect(self, module, original, replacement):
        text = module.read_text()
        self.assertIn(original, text, f"{module.name} no longer defines {original}")
        module.write_text(text.replace(original, replacement))

    def write_live_publication(self, sources):
        """A fake live publication: Release and an uncompressed Packages index
        with one binary stanza per source name (a file tree, nothing runs)."""
        dist = self.public / "dists" / SERIES
        (dist / "main" / "binary-amd64").mkdir(parents=True, exist_ok=True)
        (dist / "Release").write_text("Origin: . resolute\nLabel: . resolute\nSuite: resolute\nCodename: resolute\n"
                                      "Components: main\nArchitectures: amd64\nDate: Thu, 01 Jan 2099 00:00:00 UTC\n")
        stanzas = [f"Package: {name}-bin\nSource: {name} (0.1)\nVersion: 0.1\nArchitecture: amd64\n"
                   f"Filename: pool/main/{name[0]}/{name}/{name}-bin_0.1_amd64.deb\nSize: 1\nSHA256: {'0' * 64}\n"
                   for name in sources]
        (dist / "main" / "binary-amd64" / "Packages").write_text("\n".join(stanzas))

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

    def board(self, state, evidence="-", owner="A"):
        (self.home / "coordinator" / "TASKS.md").write_text(
            "| ID | Title | Owner | Machine | State | Claimed | Heartbeat | Updated | Evidence |\n"
            f"| {TASK} | demo | {owner} | target | {state} | x | x | x | {evidence} |\n")

    def run_script(self, *argv, allow_aptly=False):
        result = subprocess.run([sys.executable, *argv], cwd=self.root, env=self.env,
                                capture_output=True, text=True, timeout=120)
        if not allow_aptly:
            self.assertFalse(self.aptly_log.exists(),
                             f"aptly was called: {self.aptly_log.read_text() if self.aptly_log.exists() else ''}")
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

    def write_gate(self, entries, publish=True):
        """The gate, committed and pushed to the local origin's main; the board
        and the task evidence at READY_TO_PUBLISH. Returns the gate path."""
        manifest = self.write_manifest(entries)
        gate = self.root / "rec" / "gate.json"
        extra = getattr(self, "gate_extra", {})
        if callable(extra):
            extra = extra(json.loads(manifest.read_text()))
        content = {**extra,
                   "schema": 1, "task_id": TASK, "package": PACKAGE, "candidate_version": VERSION,
                   "target_series": SERIES, "task_state": "READY_TO_PUBLISH", "source_tree": "CLEAN",
                   "target_series_build": "PASS", "version_safety": "SAFE", "patch_and_decision_docs": "COMPLETE",
                   "source_provenance": "PUSHED", "verification_result": "PASS", "peer_notice": "ACK",
                   "source_repo": f"packages/{PACKAGE}", "source_commit": self.commit, "source_tree_hash": self.tree,
                   "source_remote_ref": "origin/main",
                   "build_manifest": {"file": str(manifest.relative_to(self.root)), "sha256": sha(manifest)}}
        if publish:
            content.setdefault("publish", {"operation": "switch", "distribution": SERIES, "prefix": ".",
                                           "snapshot": f"unity-{SERIES}-{TASK}"})
            # a committed evidence manifest, so C's approval can pin it; its
            # content is not what these fixtures test (the publisher refuses it
            # later as incomplete)
            evidence_manifest = self.root / "rec" / "evidence-manifest.json"
            evidence_manifest.write_text(json.dumps({"schema": 1, "task_id": TASK, "package": PACKAGE,
                                                     "source_commit": self.commit, "files": {}}))
            content.setdefault("evidence_manifest", {"file": "rec/evidence-manifest.json",
                                                     "sha256": sha(evidence_manifest)})
        gate.write_text(json.dumps(content))
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
        return gate

    def approve(self, *extra, actor="C", branch="main"):
        """C's approval through the copied taskctl.py (permission model phase 4)."""
        return self.run_script("scripts/taskctl.py", "approve-publication", TASK, "--actor", actor,
                               "--repo", str(self.root), "--branch", branch, *extra)

    def publish(self, entries, approved=True):
        """Runs the publisher on a gate; with approved=True C's approval is
        recorded first. Without one the publisher stops at the approval; with
        one it stops at its next unmet check (the evidence manifest file)."""
        gate = self.write_gate(entries)
        if approved:
            result = self.approve()
            self.assertEqual(result.returncode, 0, result.stderr)
        return self.run_script("scripts/publish_aptly.py", "--gate", str(gate))
