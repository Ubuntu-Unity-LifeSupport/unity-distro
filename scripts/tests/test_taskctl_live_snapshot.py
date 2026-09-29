#!/usr/bin/env python3
"""UNITY-20260929-015: taskctl's PUBLISHED gate accepts a live snapshot other
than the recorded one only if it carries every artifact of the publish record
with the recorded version and sha256 (scripts/taskctl.py confirm_live_publication).

The unit tests fake every aptly call. The integration test runs real, read-only
aptly snapshot commands against a scratch aptly root; only `publish show` is
faked there, since nothing is published.
Run: python3 -m unittest discover -s scripts/tests
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import taskctl  # noqa: E402

DSC_SHA = "d" * 64
TAR_SHA = "t" * 64
BIN_SHA = "b" * 64
DBG_SHA = "g" * 64


def record(**overrides):
    base = {
        "snapshot": "repo-20990101-001",
        "artifacts": [
            {"file": "demo_1.0+unity1.dsc", "sha256": DSC_SHA, "kind": "source", "package": "demo",
             "version": "1:1.0+unity1", "architecture": "source"},
            {"file": "demo_1.0+unity1.tar.xz", "sha256": TAR_SHA, "kind": "source_file", "package": "demo",
             "version": "1:1.0+unity1", "architecture": None},
            {"file": "demo-bin_1.0+unity1_amd64.deb", "sha256": BIN_SHA, "kind": "binary", "package": "demo-bin",
             "version": "1:1.0+unity1", "architecture": "amd64"},
            {"file": "demo-bin-dbgsym_1.0+unity1_amd64.ddeb", "sha256": DBG_SHA, "kind": "binary",
             "package": "demo-bin-dbgsym", "version": "1:1.0+unity1", "architecture": "amd64"},
            {"file": "demo_1.0+unity1_amd64.buildinfo", "sha256": "i" * 64, "kind": "buildinfo", "package": "demo",
             "version": "1:1.0+unity1", "architecture": "amd64"},
            {"file": "demo_1.0+unity1_amd64.changes", "sha256": "c" * 64, "kind": "changes", "package": "demo",
             "version": "1:1.0+unity1", "architecture": "amd64"},
        ],
    }
    base.update(overrides)
    return base


def show(*sources):
    lines = ["Prefix: .", "Distribution: resolute", "Architectures: amd64 source", "Sources:"]
    return "\n".join(lines + [f"  {component}: {name} [{kind}]" for component, name, kind in sources]) + "\n"


class Done:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


class FakeAptly:
    """Answers taskctl's read-only aptly calls from a small in-memory snapshot."""

    def __init__(self, shown, binaries=None, sources=None):
        self.shown = shown
        # {(package, version, arch): [sha256, ...]} and {(package, version): [{file: sha256}, ...]}
        self.binaries = binaries if binaries is not None else {
            ("demo-bin", "1:1.0+unity1", "amd64"): [BIN_SHA],
            ("demo-bin-dbgsym", "1:1.0+unity1", "amd64"): [DBG_SHA],
            ("other", "2.0", "amd64"): ["o" * 64]}
        self.sources = sources if sources is not None else {
            ("demo", "1:1.0+unity1"): [{"demo_1.0+unity1.dsc": DSC_SHA, "demo_1.0+unity1.tar.xz": TAR_SHA}]}
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["publish", "show"]:
            return self.shown if isinstance(self.shown, Done) else Done(stdout=self.shown)
        assert args[:2] == ["snapshot", "search"], args
        assert "publish" not in args, args
        fmt, query = args[3], args[5]
        parts = dict(p.strip().rstrip(")").split(" (", 1) for p in query.split(","))
        version = parts["Version"].removeprefix("= ")
        if "$Architecture" in parts:
            found = self.sources.get((parts["Name"], version), [])
            if not found:
                return Done(1, "", "ERROR: no results")
            if fmt == "{{.Key}}":
                return Done(stdout="".join(f"Psource {parts['Name']} {version} {i}\n" for i in range(len(found))))
            return Done(stdout="".join(f" {sha} 1 {name}\n" for files in found for name, sha in files.items()) + "\n")
        found = self.binaries.get((parts["Name"], version, parts["Architecture"]), [])
        return Done(stdout="".join(s + "\n" for s in found)) if found else Done(1, "", "ERROR: no results")


class ConfirmLivePublicationTest(unittest.TestCase):
    def confirm(self, fake, rec=None):
        return taskctl.confirm_live_publication(rec or record(), "resolute", ".", run=fake)

    def test_recorded_snapshot_live(self):
        fake = FakeAptly(show(("main", "repo-20990101-001", "snapshot")))
        self.assertIsNone(self.confirm(fake))
        self.assertEqual(fake.calls, [["publish", "show", "resolute"]])

    def test_prefix_passed_when_not_dot(self):
        fake = FakeAptly(show(("main", "repo-20990101-001", "snapshot")))
        self.assertIsNone(taskctl.confirm_live_publication(record(), "resolute", "candidate", run=fake))
        self.assertEqual(fake.calls[0], ["publish", "show", "resolute", "candidate"])

    def test_later_superset_snapshot_accepted(self):
        """The regression: -021 after -019 switched ./resolute."""
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")))
        self.assertIsNone(self.confirm(fake))
        searched = [c for c in fake.calls if c[:2] == ["snapshot", "search"]]
        self.assertTrue(searched and all(c[4] == "repo-20990101-002" for c in searched))
        self.assertTrue(any("Name (demo-bin-dbgsym), Version (= 1:1.0+unity1), Architecture (amd64)" in c for c in searched))

    def test_binary_removed_refused(self):
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")))
        del fake.binaries[("demo-bin", "1:1.0+unity1", "amd64")]
        error = self.confirm(fake)
        self.assertIn("missing ['demo-bin 1:1.0+unity1 amd64']", error)

    def test_binary_replaced_by_other_version_refused(self):
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")))
        del fake.binaries[("demo-bin", "1:1.0+unity1", "amd64")]
        fake.binaries[("demo-bin", "1:1.0+unity2", "amd64")] = ["n" * 64]
        self.assertIn("missing ['demo-bin 1:1.0+unity1 amd64']", self.confirm(fake))

    def test_binary_rebuilt_same_version_other_bytes_refused(self):
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")))
        fake.binaries[("demo-bin-dbgsym", "1:1.0+unity1", "amd64")] = ["x" * 64]
        self.assertIn("other sha256 ['demo-bin-dbgsym 1:1.0+unity1 amd64']", self.confirm(fake))

    def test_binary_twice_refused(self):
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")))
        fake.binaries[("demo-bin", "1:1.0+unity1", "amd64")] = [BIN_SHA, "x" * 64]
        self.assertIn("other sha256 ['demo-bin 1:1.0+unity1 amd64']", self.confirm(fake))

    def test_source_missing_refused(self):
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")), sources={})
        self.assertIn("missing ['demo 1:1.0+unity1 source']", self.confirm(fake))

    def test_source_file_other_hash_refused(self):
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")), sources={
            ("demo", "1:1.0+unity1"): [{"demo_1.0+unity1.dsc": DSC_SHA, "demo_1.0+unity1.tar.xz": "x" * 64}]})
        self.assertIn("other hash ['demo_1.0+unity1.tar.xz']", self.confirm(fake))

    def test_two_source_packages_same_version_refused(self):
        files = {"demo_1.0+unity1.dsc": DSC_SHA, "demo_1.0+unity1.tar.xz": TAR_SHA}
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")),
                         sources={("demo", "1:1.0+unity1"): [files, dict(files)]})
        self.assertIn("found 2 source packages", self.confirm(fake))

    def test_two_components_refused(self):
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot"), ("contrib", "x-001", "snapshot")))
        self.assertIn("is not exactly one snapshot", self.confirm(fake))
        self.assertEqual(len(fake.calls), 1)

    def test_local_repo_source_refused(self):
        fake = FakeAptly(show(("main", "unity-resolute", "local")))
        self.assertIn("is not exactly one snapshot", self.confirm(fake))

    def test_publish_show_failure_refused(self):
        fake = FakeAptly(Done(1, "", "ERROR: unable to show: published repo not found"))
        self.assertIn("failed: ERROR: unable to show", self.confirm(fake))

    def test_record_without_binary_or_source_refused(self):
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")))
        for drop in ("binary", "source", "source_file"):
            with self.subTest(drop=drop):
                rec = record()
                rec["artifacts"] = [a for a in rec["artifacts"] if a["kind"] != drop]
                self.assertIn("exactly one source, its source files and at least one binary", self.confirm(fake, rec))
        self.assertIn("exactly one source", self.confirm(fake, record(artifacts=[])))

    def test_unknown_artifact_kind_refused(self):
        rec = record()
        rec["artifacts"].append({"file": "demo.udeb", "sha256": "u" * 64, "kind": "udeb", "package": "demo-udeb",
                                 "version": "1:1.0+unity1", "architecture": "amd64"})
        fake = FakeAptly(show(("main", "repo-20990101-002", "snapshot")))
        self.assertIn("without a live-content rule: ['udeb']", self.confirm(fake, rec))


@unittest.skipUnless(shutil.which("aptly") and shutil.which("dpkg-source") and os.geteuid() != 0,
                     "needs aptly, dpkg-source and a non-root user")
class ConfirmLivePublicationAptlyTest(unittest.TestCase):
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

    def deb(self, out, name, version, marker="1"):
        root = self.t / f".b-{name}-{version}-{marker}"
        (root / "DEBIAN").mkdir(parents=True)
        (root / "DEBIAN" / "control").write_text(
            f"Package: {name}\nVersion: {version}\nArchitecture: amd64\nSource: demo\n"
            f"Maintainer: t <t@example.com>\nDescription: t {marker}\n")
        path = out / f"{name}_{version.split(':', 1)[-1]}_amd64.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(path)],
                       check=True, capture_output=True)
        return path

    def source(self, out, version):
        src = self.t / "demo-src"
        (src / "debian" / "source").mkdir(parents=True)
        (src / "debian" / "source" / "format").write_text("3.0 (native)\n")
        (src / "debian" / "control").write_text(
            "Source: demo\nMaintainer: t <t@example.com>\n\nPackage: demo-bin\nArchitecture: amd64\nDescription: t\n")
        (src / "debian" / "changelog").write_text(
            f"demo ({version}) resolute; urgency=medium\n\n  * t\n\n -- t <t@example.com>  Tue, 29 Sep 2026 00:00:00 +0000\n")
        subprocess.run(["dpkg-source", "-b", str(src)], cwd=out, check=True, capture_output=True)
        return sorted(out.glob("demo_*"))

    def sha(self, path):
        return taskctl.sha256(path)

    def run_fake_show(self, live):
        def run(args):
            if args[:2] == ["publish", "show"]:
                return Done(stdout=show(("main", live, "snapshot")))
            return subprocess.run(["aptly", f"-config={self.conf}"] + args, check=False, capture_output=True, text=True)
        return run

    def test_real_snapshots(self):
        version = "1:1.0+unity1"
        first, extra, rebuilt = self.t / "first", self.t / "extra", self.t / "rebuilt"
        for d in (first, extra, rebuilt):
            d.mkdir()
        dsc, tar = self.source(first, version)
        binary = self.deb(first, "demo-bin", version)
        rec = {"snapshot": "s-021", "artifacts": [
            {"file": dsc.name, "sha256": self.sha(dsc), "kind": "source", "package": "demo", "version": version,
             "architecture": "source"},
            {"file": tar.name, "sha256": self.sha(tar), "kind": "source_file", "package": "demo", "version": version,
             "architecture": None},
            {"file": binary.name, "sha256": self.sha(binary), "kind": "binary", "package": "demo-bin",
             "version": version, "architecture": "amd64"}]}
        self.aptly("repo", "create", "r")
        self.aptly("repo", "add", "r", str(first))
        self.aptly("snapshot", "create", "s-021", "from", "repo", "r")
        self.deb(extra, "lightdm-demo", "2.0")
        self.aptly("repo", "add", "r", str(extra))
        self.aptly("snapshot", "create", "s-019", "from", "repo", "r")
        # same version, other bytes, in its own repo (aptly refuses the conflict within one repo)
        self.deb(rebuilt, "demo-bin", version, marker="rebuilt")
        self.aptly("repo", "create", "r2")
        self.aptly("repo", "add", "r2", str(rebuilt))
        self.aptly("repo", "add", "r2", str(dsc))
        self.aptly("snapshot", "create", "s-rebuilt", "from", "repo", "r2")

        self.assertIsNone(taskctl.confirm_live_publication(rec, "resolute", ".", run=self.run_fake_show("s-021")))
        self.assertIsNone(taskctl.confirm_live_publication(rec, "resolute", ".", run=self.run_fake_show("s-019")))
        error = taskctl.confirm_live_publication(rec, "resolute", ".", run=self.run_fake_show("s-rebuilt"))
        self.assertIn("other sha256 ['demo-bin 1:1.0+unity1 amd64']", error)
        self.aptly("repo", "remove", "r", "demo-bin")
        self.aptly("snapshot", "create", "s-removed", "from", "repo", "r")
        error = taskctl.confirm_live_publication(rec, "resolute", ".", run=self.run_fake_show("s-removed"))
        self.assertIn("missing ['demo-bin 1:1.0+unity1 amd64']", error)


if __name__ == "__main__":
    unittest.main()
