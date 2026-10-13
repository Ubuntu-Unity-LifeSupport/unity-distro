#!/usr/bin/env python3
"""UNITY-20261008-002: before the switch, publish_aptly.py checks the gated
snapshot by bytes, not only by name: every manifest binary exactly once with
its sha256, and exactly one source package made of the build's .dsc and files
(scripts/publish_aptly.py check_gated_snapshot, snapshot_content). taskctl's
live-snapshot check uses the same snapshot_content (UNITY-20260929-015).

The unit tests fake every aptly call. The integration test runs real, read-only
aptly snapshot commands against a scratch aptly root with its own -config.
The wiring test reads publish_aptly.main()'s syntax tree.
Run: python3 -m unittest discover -s scripts/tests
"""

import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_taskctl_live_snapshot import (  # noqa: E402
    BIN_SHA, DBG_SHA, DSC_SHA, TAR_SHA, Done, FakeAptly, record)

spec = importlib.util.spec_from_file_location("publish_aptly", HERE.parent / "publish_aptly.py")
publish_aptly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish_aptly)

SNAPSHOT = "unity-resolute-20990101-001"
NAMES = ["demo_1:1.0+unity1_source", "demo-bin_1:1.0+unity1_amd64", "demo-bin-dbgsym_1:1.0+unity1_amd64"]


class FakeSnapshot(FakeAptly):
    """FakeAptly plus `snapshot show -with-packages` for the gated snapshot."""

    def __init__(self, listed=NAMES, **kwargs):
        super().__init__(shown="", **kwargs)
        self.listed = listed

    def __call__(self, args):
        if args[:2] == ["snapshot", "show"]:
            self.calls.append(args)
            assert args == ["snapshot", "show", "-with-packages", SNAPSHOT], args
            return Done(stdout="Name: x\nPackages:\n" + "".join(f"  {n}\n" for n in self.listed))
        assert args[:2] == ["snapshot", "search"] and args[4] == SNAPSHOT, args
        return super().__call__(args)


class CheckGatedSnapshotTest(unittest.TestCase):
    def check(self, fake):
        return publish_aptly.check_gated_snapshot(SNAPSHOT, NAMES, record()["artifacts"], run=fake)

    def test_matching_snapshot_accepted(self):
        fake = FakeSnapshot()
        self.assertIsNone(self.check(fake))
        searched = [c[5] for c in fake.calls if c[:2] == ["snapshot", "search"]]
        self.assertIn("Name (demo-bin), Version (= 1:1.0+unity1), Architecture (amd64)", searched)
        self.assertIn("Name (demo-bin-dbgsym), Version (= 1:1.0+unity1), Architecture (amd64)", searched)

    def test_name_missing_refused(self):
        error = self.check(FakeSnapshot(listed=NAMES[:2]))
        self.assertIn("does not contain expected artifact demo-bin-dbgsym_1:1.0+unity1_amd64", error)

    def test_snapshot_show_failure_refused(self):
        error = self.check(lambda args: Done(1, "", "ERROR: snapshot not found"))
        self.assertIn("aptly cannot inspect snapshot", error)

    def test_binary_same_version_other_bytes_refused(self):
        """The gap: a rebuild of the same version in the repository."""
        fake = FakeSnapshot()
        fake.binaries[("demo-bin", "1:1.0+unity1", "amd64")] = ["x" * 64]
        self.assertIn("other sha256 ['demo-bin 1:1.0+unity1 amd64']", self.check(fake))

    def test_ddeb_other_bytes_refused(self):
        fake = FakeSnapshot()
        fake.binaries[("demo-bin-dbgsym", "1:1.0+unity1", "amd64")] = ["x" * 64]
        self.assertIn("other sha256 ['demo-bin-dbgsym 1:1.0+unity1 amd64']", self.check(fake))

    def test_binary_twice_refused(self):
        fake = FakeSnapshot()
        fake.binaries[("demo-bin", "1:1.0+unity1", "amd64")] = [BIN_SHA, BIN_SHA]
        self.assertIn("other sha256 ['demo-bin 1:1.0+unity1 amd64']", self.check(fake))

    def test_binary_not_found_refused(self):
        fake = FakeSnapshot()
        del fake.binaries[("demo-bin", "1:1.0+unity1", "amd64")]
        self.assertIn("missing ['demo-bin 1:1.0+unity1 amd64']", self.check(fake))

    def test_source_missing_refused(self):
        self.assertIn("missing ['demo 1:1.0+unity1 source']", self.check(FakeSnapshot(sources={})))

    def test_source_file_other_hash_refused(self):
        fake = FakeSnapshot(sources={("demo", "1:1.0+unity1"): [
            {"demo_1.0+unity1.dsc": DSC_SHA, "demo_1.0+unity1.tar.xz": "x" * 64}]})
        self.assertIn("other hash ['demo_1.0+unity1.tar.xz']", self.check(fake))

    def test_two_source_packages_refused(self):
        files = {"demo_1.0+unity1.dsc": DSC_SHA, "demo_1.0+unity1.tar.xz": TAR_SHA}
        fake = FakeSnapshot(sources={("demo", "1:1.0+unity1"): [files, dict(files)]})
        self.assertIn("found 2 source packages", self.check(fake))

    def test_default_run_is_looked_up_at_call_time(self):
        fake = FakeSnapshot()
        saved = publish_aptly.run_aptly
        publish_aptly.run_aptly = fake
        try:
            self.assertIsNone(publish_aptly.check_gated_snapshot(SNAPSHOT, NAMES, record()["artifacts"]))
        finally:
            publish_aptly.run_aptly = saved
        self.assertTrue(fake.calls)

    def test_taskctl_uses_the_same_check(self):
        """One rule for the publisher and taskctl's PUBLISHED gate."""
        sys.path.insert(0, str(HERE.parent))
        import taskctl
        source = Path(taskctl.__file__).read_text(encoding="utf-8")
        self.assertIn("missing, differing = snapshot_content(artifacts, live, run)", source)
        self.assertNotIn('{{index . "SHA256"}}', source)


class MainWiringTest(unittest.TestCase):
    """main() makes exactly one check_gated_snapshot call, refuses on its result,
    before the switch-time apt view and the START log, with no inline snapshot search."""

    def setUp(self):
        tree = ast.parse((HERE.parent / "publish_aptly.py").read_text(encoding="utf-8"))
        self.main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")

    def calls(self, name):
        return [n for n in ast.walk(self.main) if isinstance(n, ast.Call)
                and getattr(n.func, "id", getattr(n.func, "attr", None)) == name]

    def test_one_call_refusing_on_its_result(self):
        calls = self.calls("check_gated_snapshot")
        self.assertEqual(len(calls), 1)
        assign = next(n for n in ast.walk(self.main) if isinstance(n, ast.Assign) and n.value is calls[0])
        target = assign.targets[0].id
        refusing = [n for n in ast.walk(self.main) if isinstance(n, ast.If)
                    and isinstance(n.test, ast.Name) and n.test.id == target
                    and any(isinstance(c, ast.Call) and getattr(c.func, "id", None) == "fail"
                            and any(isinstance(a, ast.Name) and a.id == target for a in c.args)
                            for s in n.body for c in ast.walk(s))]
        self.assertEqual(len(refusing), 1, "the check's result must be passed to fail() when set")

    def test_before_apt_view_and_start(self):
        line = self.calls("check_gated_snapshot")[0].lineno
        apt_view = [n.lineno for n in ast.walk(self.main) if isinstance(n, ast.Constant) and n.value == "scripts/apt_view.py"]
        start = [c.lineno for c in self.calls("log_event")
                 if c.args and isinstance(c.args[0], ast.Constant) and c.args[0].value == "START"]
        self.assertTrue(apt_view and start)
        self.assertLess(line, min(apt_view))
        self.assertLess(line, min(start))

    def test_no_inline_snapshot_search(self):
        self.assertEqual(self.calls("source_package_matches"), [])
        constants = [n.value for n in ast.walk(self.main) if isinstance(n, ast.Constant)]
        self.assertNotIn("search", constants)


@unittest.skipUnless(shutil.which("aptly") and shutil.which("dpkg-source") and os.geteuid() != 0,
                     "needs aptly, dpkg-source and a non-root user")
class CheckGatedSnapshotAptlyTest(unittest.TestCase):
    """Real snapshots in a scratch aptly root; the same -config for every call."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.conf = self.t / "aptly.conf"
        self.conf.write_text(json.dumps({"rootDir": str(self.t / "aptly"), "gpgDisableSign": True,
                                         "gpgDisableVerify": True}))

    def tearDown(self):
        self.tmp.cleanup()

    def aptly(self, *args):
        return subprocess.run(["aptly", f"-config={self.conf}"] + list(args), check=True, capture_output=True, text=True)

    def run_scratch(self, args):
        return subprocess.run(["aptly", f"-config={self.conf}"] + args, check=False, capture_output=True, text=True)

    def deb(self, out, name, version, marker):
        root = self.t / f".b-{name}-{marker}"
        (root / "DEBIAN").mkdir(parents=True)
        (root / "DEBIAN" / "control").write_text(
            f"Package: {name}\nVersion: {version}\nArchitecture: amd64\nSource: demo\n"
            f"Maintainer: t <t@example.com>\nDescription: t {marker}\n")
        path = out / f"{name}_{version.split(':', 1)[-1]}_amd64.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(path)],
                       check=True, capture_output=True)
        return path

    def test_real_snapshots(self):
        version = "1:1.0+unity1"
        built, rebuilt = self.t / "built", self.t / "rebuilt"
        built.mkdir(); rebuilt.mkdir()
        src = self.t / "demo-src"
        (src / "debian" / "source").mkdir(parents=True)
        (src / "debian" / "source" / "format").write_text("3.0 (native)\n")
        (src / "debian" / "control").write_text(
            "Source: demo\nMaintainer: t <t@example.com>\n\nPackage: demo-bin\nArchitecture: amd64\nDescription: t\n")
        (src / "debian" / "changelog").write_text(
            f"demo ({version}) resolute; urgency=medium\n\n  * t\n\n -- t <t@example.com>  Tue, 29 Sep 2026 00:00:00 +0000\n")
        subprocess.run(["dpkg-source", "-b", str(src)], cwd=built, check=True, capture_output=True)
        dsc, tar = sorted(built.glob("demo_*"))
        gated = self.deb(built, "demo-bin", version, "gated")
        other = self.deb(rebuilt, "demo-bin", version, "rebuilt")
        sha = publish_aptly.sha256
        artifacts = [
            {"file": dsc.name, "sha256": sha(dsc), "kind": "source", "package": "demo", "version": version},
            {"file": tar.name, "sha256": sha(tar), "kind": "source_file", "package": "demo", "version": version},
            {"file": gated.name, "sha256": sha(gated), "kind": "binary", "package": "demo-bin",
             "version": version, "architecture": "amd64"}]
        names = [f"demo_{version}_source", f"demo-bin_{version}_amd64"]
        self.aptly("repo", "create", "good")
        self.aptly("repo", "add", "good", str(dsc), str(gated))
        self.aptly("snapshot", "create", "s-good", "from", "repo", "good")
        self.aptly("repo", "create", "bad")
        self.aptly("repo", "add", "bad", str(dsc), str(other))
        self.aptly("snapshot", "create", "s-rebuilt", "from", "repo", "bad")

        self.assertIsNone(publish_aptly.check_gated_snapshot("s-good", names, artifacts, run=self.run_scratch))
        error = publish_aptly.check_gated_snapshot("s-rebuilt", names, artifacts, run=self.run_scratch)
        self.assertIn("other sha256 ['demo-bin 1:1.0+unity1 amd64']", error)


if __name__ == "__main__":
    unittest.main()
