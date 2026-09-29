#!/usr/bin/env python3
"""Tests for scripts/tested_build.py (UNITY-20260929-020): the link between
what the target test installed and the gated build, in each mode, as the
release gate and the publisher check it.
Run: python3 -m unittest discover -s scripts/tests
"""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tested_build as tb  # noqa: E402

H = lambda text: hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()
DEB, DEB2 = "demo_1.0+unity1_amd64.deb", "libdemo1_1.0+unity1_amd64.deb"
IBD = ("Installed-Build-Depends:\n autoconf (= 2.72-3),\n libc6:amd64 (= 2.43-2ubuntu2),\n"
       " libnux-4.0-dev (= 4.0.8-0ubuntu15+unity2)\n")


def buildinfo(version="1.0+unity1", arch="amd64", ibd=IBD, source="demo"):
    return f"Format: 1.0\nSource: {source}\nBinary: demo\nVersion: {version}\nBuild-Architecture: {arch}\n{ibd}Environment:\n X=1\n"


class TestedBuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        self.git("init", "-q")
        # the gated build (its dir need not be committed: the gate hashes the manifest itself)
        self.gdir = self.root / "gated"
        self.gdir.mkdir()
        self.debs = {DEB: H("deb-bytes"), DEB2: H("deb2-bytes")}
        (self.gdir / "demo_1.0+unity1_amd64.buildinfo").write_text(buildinfo())
        self.chroot_sha = H("tarball")
        self.manifest = {
            "schema": 1, "source_commit": "c" * 40, "source_tree_hash": "t" * 40,
            "artifacts": [{"file": DEB, "sha256": self.debs[DEB], "kind": "binary"},
                          {"file": DEB2, "sha256": self.debs[DEB2], "kind": "binary"},
                          {"file": "demo_1.0+unity1_amd64.buildinfo", "kind": "buildinfo",
                           "sha256": H(buildinfo())}],
            "chroot": {"sha256": self.chroot_sha},
            "build_dependencies": [{"package": "libnux-4.0-dev", "version": "4.0.8-0ubuntu15+unity2",
                                    "architecture": "amd64", "sha256": H("nux"), "file": "build-dependencies/x.deb"}],
        }
        # the tested build: its manifest and .buildinfo; the target test record
        tested = copy.deepcopy(self.manifest)
        tested["artifacts"][2]["sha256"] = H(buildinfo())
        tested["build_dependencies"][0]["file"] = "build-dependencies/other-path.deb"  # paths may differ
        self.write("tested/manifest.json", json.dumps(tested))
        self.write("tested/demo_1.0+unity1_amd64.buildinfo", buildinfo())
        self.write("tests/target-test.txt", f"installed {DEB} and {DEB2} with apt-get install ./*.deb\n")
        self.commit()
        self.manifest["chroot"]["tested_with"] = {"manifest_sha256": H(json.dumps(tested)), "chroot_sha256": self.chroot_sha}

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True,
                              text=True, env=self.env).stdout

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "x", "--allow-empty")

    def fields(self, mode, **extra):
        f = {"tested_build": mode, "target_test": {"record": "tests/target-test.txt", "debs": dict(self.debs)}}
        f.update(extra)
        return f

    def check(self, fields, manifest=None):
        return tb.check(fields, manifest or self.manifest, self.gdir, self.root)

    MODES = {
        "this_build": {},
        "same_chroot": {"tested_manifest": "tested/manifest.json"},
        "buildinfo_identical": {"tested_buildinfo": "tested/demo_1.0+unity1_amd64.buildinfo",
                                "tested_manifest": "tested/manifest.json"},
    }

    def mode_fields(self, label):
        return self.fields(label.split(" ")[0], **self.MODES[label])

    def test_each_mode_accepted_and_recomputed(self):
        for label in self.MODES:
            with self.subTest(mode=label):
                result, error = self.check(self.mode_fields(label))
                self.assertIsNone(error)
                self.assertEqual(result["mode"], label.split(" ")[0])
                self.assertEqual(result["target_test"]["debs"], self.debs)
                # the publisher recomputes exactly the gate's object
                self.assertIsNone(tb.publish_error(result, self.manifest, self.gdir, self.root))

    def test_common_refusals(self):
        for label in self.MODES:
            cases = {
                "no chroot in the gated manifest": (self.mode_fields(label), {k: v for k, v in self.manifest.items() if k != "chroot"}),
                "unknown mode": (dict(self.mode_fields(label), tested_build="trust_me"), None),
                "no target_test": ({k: v for k, v in self.mode_fields(label).items() if k != "target_test"}, None),
                "empty debs": (dict(self.mode_fields(label), target_test={"record": "tests/target-test.txt", "debs": {}}), None),
                "deb hash mismatch": (dict(self.mode_fields(label), target_test={"record": "tests/target-test.txt",
                                           "debs": dict(self.debs, **{DEB: H("other")})}), None),
                "deb not built": (dict(self.mode_fields(label), target_test={"record": "tests/target-test.txt",
                                       "debs": dict(self.debs, **{"evil_1_all.deb": H("evil")})}), None),
                "record missing": (dict(self.mode_fields(label), target_test={"record": "tests/none.txt", "debs": self.debs}), None),
                "record outside the repository": (dict(self.mode_fields(label), target_test={"record": "../x.txt", "debs": self.debs}), None),
            }
            for case, (fields, manifest) in cases.items():
                with self.subTest(mode=label, case=case):
                    self.assertIsNotNone(self.check(fields, manifest)[1])

    def test_record_must_name_each_deb_and_be_committed(self):
        self.write("tests/target-test.txt", f"installed {DEB} only\n")
        self.commit()
        self.assertIn("does not name", self.check(self.fields("this_build"))[1])
        self.write("tests/target-test.txt", f"installed {DEB} and {DEB2}\n")  # fixed but uncommitted
        self.assertIn("committed", self.check(self.fields("this_build"))[1])

    def test_this_build_binary_artifacts_only(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["artifacts"][1]["kind"] = "source_file"
        self.assertIsNotNone(self.check(self.fields("this_build"), manifest)[1])

    def test_same_chroot_refusals(self):
        f = self.mode_fields("same_chroot")
        for case, change in {
            "not built --tested-with this manifest": lambda m: m["chroot"]["tested_with"].update(manifest_sha256=H("x")),
            "no tested_with": lambda m: m["chroot"].pop("tested_with"),
            "other chroot": lambda m: m["chroot"].update(sha256=H("other")),
            "other source commit": lambda m: m.update(source_commit="d" * 40),
            "other source tree": lambda m: m.update(source_tree_hash="u" * 40),
            "other extra package": lambda m: m["build_dependencies"][0].update(version="4.0.8-0ubuntu16"),
            "extra package dropped": lambda m: m.pop("build_dependencies"),
        }.items():
            with self.subTest(case=case):
                manifest = copy.deepcopy(self.manifest)
                change(manifest)
                self.assertIsNotNone(self.check(f, manifest)[1])

    def test_tested_manifest_committed_and_unchanged(self):
        f = self.mode_fields("same_chroot")
        self.write("tested/manifest.json", (self.root / "tested/manifest.json").read_text() + " ")
        self.assertIn("committed", self.check(f)[1])  # modified, uncommitted
        self.commit()
        self.assertIn("manifest_sha256", self.check(f)[1])  # committed, but not the one --tested-with named

    def test_buildinfo_identical_refusals(self):
        f = self.mode_fields("buildinfo_identical")
        for case, text in {
            "Binary": buildinfo().replace("Binary: demo", "Binary: demo demo-extra"),
            "Architecture": buildinfo().replace("Format: 1.0", "Format: 1.0\nArchitecture: all"),
            "duplicate entry": buildinfo(ibd=IBD.replace(" autoconf (= 2.72-3),", " autoconf (= 9.9),\n autoconf (= 2.72-3),")),
            "one version differs": buildinfo(ibd=IBD.replace("2.72-3", "2.72-4")),
            "one entry more": buildinfo(ibd=IBD.rstrip("\n") + ",\n zlib1g (= 1:1.3)\n"),
            "one entry less": buildinfo(ibd=IBD.replace(",\n autoconf (= 2.72-3)", "").replace(" autoconf (= 2.72-3),\n", "")),
            "arch qualifier": buildinfo(ibd=IBD.replace("libc6:amd64", "libc6")),
            "Source": buildinfo(source="other"),
            "Version": buildinfo(version="1.0+unity2"),
            "Build-Architecture": buildinfo(arch="arm64"),
        }.items():
            with self.subTest(case=case):
                (self.gdir / "demo_1.0+unity1_amd64.buildinfo").write_text(text)
                manifest = copy.deepcopy(self.manifest)
                manifest["artifacts"][2]["sha256"] = H(text)
                self.assertIsNotNone(self.check(f, manifest)[1])

    def test_buildinfo_identical_needs_the_tested_source(self):
        """Verifier round 1: the same version from another source tree, or other
        extra-package bytes, is not the tested build; a tested manifest is required."""
        f = self.mode_fields("buildinfo_identical")
        for case, change in {
            "same version, other source tree": lambda m: m.update(source_tree_hash="u" * 40),
            "same version, other source commit": lambda m: m.update(source_commit="d" * 40),
            "same version, other extra-package bytes": lambda m: m["build_dependencies"][0].update(sha256=H("other nux")),
        }.items():
            with self.subTest(case=case):
                manifest = copy.deepcopy(self.manifest)
                change(manifest)
                self.assertIn("differ in", self.check(f, manifest)[1])
        self.assertIsNotNone(self.check({k: v for k, v in f.items() if k != "tested_manifest"})[1])

    def test_tested_manifest_needs_source_fields(self):
        f = self.mode_fields("buildinfo_identical")
        tested = json.loads((self.root / "tested/manifest.json").read_text())
        for case, change in {"no source_commit": lambda t: t.pop("source_commit"),
                             "empty source_tree_hash": lambda t: t.update(source_tree_hash=""),
                             "schema 0": lambda t: t.update(schema=0)}.items():
            with self.subTest(case=case):
                t = copy.deepcopy(tested)
                change(t)
                self.write("tested/manifest.json", json.dumps(t))
                self.commit()
                self.assertIn("source commit and tree", self.check(f)[1])

    def test_legacy_tested_manifest_accepted(self):
        """A tested manifest from before UNITY-20260929-016 (no chroot) is fine in buildinfo_identical."""
        tested = json.loads((self.root / "tested/manifest.json").read_text())
        tested.pop("chroot")
        self.write("tested/manifest.json", json.dumps(tested))
        self.commit()
        result, error = self.check(self.mode_fields("buildinfo_identical"))
        self.assertIsNone(error)
        self.assertIsNone(tb.publish_error(result, self.manifest, self.gdir, self.root))

    def test_record_names_whole_file_names(self):
        for text in (f"installed x{DEB} and {DEB2}\n", f"installed {DEB}.bak and {DEB2}\n",
                     f"installed {self.debs[DEB]} and {DEB2}\n"):
            with self.subTest(text=text):
                self.write("tests/target-test.txt", text)
                self.commit()
                self.assertIn("does not name", self.check(self.fields("this_build"))[1])
        self.write("tests/target-test.txt", f"apt-get install ./{DEB} ./{DEB2}\n")  # a path prefix is fine
        self.commit()
        self.assertIsNone(self.check(self.fields("this_build"))[1])

    def test_paths_without_dotdot_or_symlinks(self):
        (self.root / "link").symlink_to(self.root / "tests")
        self.git("add", "link")
        self.commit()
        for rel in ("link/target-test.txt", "tests/../tests/target-test.txt"):
            with self.subTest(rel=rel):
                f = dict(self.fields("this_build"), target_test={"record": rel, "debs": self.debs})
                self.assertIsNotNone(self.check(f)[1])
        result, error = self.check(dict(self.fields("this_build"), target_test={"record": "./tests/target-test.txt",
                                                                                "debs": self.debs}))
        self.assertIsNone(error)
        self.assertEqual(result["target_test"]["record"]["file"], "tests/target-test.txt")  # normalized

    def test_publisher_refuses_changes_after_the_gate(self):
        for label in ("same_chroot", "buildinfo_identical", "this_build"):
            with self.subTest(mode=label):
                self.tearDown(); self.setUp()
                recorded, error = self.check(self.mode_fields(label))
                self.assertIsNone(error)
                self.assertIsNone(tb.publish_error(recorded, self.manifest, self.gdir, self.root))
                # a committed file changes after the gate (and is committed again)
                self.write("tests/target-test.txt", f"installed {DEB} and {DEB2}, re-written after the gate\n")
                self.commit()
                self.assertIn("does not match", tb.publish_error(recorded, self.manifest, self.gdir, self.root))
        self.assertIsNotNone(tb.publish_error(None, self.manifest, self.gdir, self.root))

    def test_publisher_refuses_an_altered_gate_record(self):
        recorded, error = self.check(self.mode_fields("same_chroot"))
        self.assertIsNone(error)
        self.assertIsNone(tb.publish_error(recorded, self.manifest, self.gdir, self.root))
        for case, forged in {
            "mode changed": dict(recorded, mode="this_build"),
            "a recorded hash changed": dict(recorded, tested_manifest={"file": "tested/manifest.json", "sha256": H("x")}),
            "an extra key": dict(recorded, note="trust me"),
        }.items():
            with self.subTest(case=case):
                self.assertIsNotNone(tb.publish_error(forged, self.manifest, self.gdir, self.root))


if __name__ == "__main__":
    unittest.main()
