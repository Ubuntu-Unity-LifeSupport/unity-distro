#!/usr/bin/env python3
"""Tests for UNITY-20260927-048: version_safety.py decides only from an
apt_view.py measurement; apt_view.py measures an isolated target apt view with
the gated snapshot as our repository; publish_aptly.py's compare_views()
refuses a switch-time view that does not continue the gate-time one.
Run: python3 -m unittest discover -s scripts/tests
"""

from datetime import datetime, timezone
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
SCRIPTS = HERE.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


version_safety = load("version_safety")
publish_aptly = load("publish_aptly")
taskctl = load("taskctl")


def manifest(version="1:1.0+unity1", binaries=(("demo-bin", None, "amd64"), ("demo-data", None, "all"))):
    arts = [{"file": "demo_1.0+unity1.dsc", "kind": "source", "package": "demo", "version": version}]
    for name, bversion, arch in binaries:
        v = bversion or version
        arts.append({"file": f"{name}_{v.split(':', 1)[-1]}_{arch}.deb", "kind": "binary",
                     "package": name, "version": v, "architecture": arch})
    arts.append({"file": "demo_1.0+unity1_amd64.changes", "kind": "changes"})
    return {"package": "demo", "candidate_version": version, "source_commit": "c0ffee", "artifacts": arts}


def view(m, pockets, candidates=None, mode="full"):
    v = {"schema": 1, "tool": "apt_view.py", "mode": mode, "source_package": "demo",
         "measured_at": "2026-09-27T20:00:00Z", "pockets": pockets, "in_archive": bool(pockets)}
    if mode == "full":
        v["snapshot"] = {"name": "s", "list_sha256": "x"}
        v["binaries"] = [{"package": a["package"], "version": a["version"], "architecture": a["architecture"],
                          "apt_candidate": (candidates or {}).get(a["package"], a["version"])}
                         for a in m["artifacts"] if a["kind"] == "binary"]
    return v


class ComparatorTest(unittest.TestCase):
    def check(self, v, m, expected, **kw):
        result = version_safety.decide(v, m, **kw)
        self.assertEqual(result["result"], expected, result["reasons"])
        return result

    def test_safe(self):
        m = manifest()
        self.check(view(m, {"resolute": "1:1.0", "resolute-updates": "1:1.0-0ubuntu0.1"}), m, "SAFE")

    def test_binnmu_binaries_judged_by_own_version(self):
        m = manifest(binaries=(("demo-bin", "1:1.0+unity1+b1", "amd64"), ("demo-bin-dbgsym", "1:1.0+unity1+b1", "amd64")))
        self.check(view(m, {"resolute": "1:1.0"}), m, "SAFE")

    def test_apt_selects_another_version(self):
        m = manifest()
        self.check(view(m, {"resolute": "1:1.0"}, {"demo-data": "1:2.0"}), m, "UNSAFE")

    def test_pocket_rules(self):
        m = manifest()
        cases = [({"resolute": "1:1.0+unity1"}, "UNSAFE"),
                 ({"resolute": "1:1.0", "resolute-backports": "1:1.1"}, "UNSAFE"),
                 ({"resolute": "1:1.0", "resolute-updates": "1:1.0+unity2"}, "REPLACES_SECURITY_UPDATE"),
                 ({"resolute": "1:1.0", "resolute-security": "1:1.0+unity1"}, "REPLACES_SECURITY_UPDATE"),
                 ({"resolute": "1:1.0", "resolute-proposed": "1:1.0+unity1"}, "BLOCKS_FUTURE_UPDATE")]
        for pockets, expected in cases:
            with self.subTest(pockets=pockets):
                self.check(view(m, pockets), m, expected)

    def test_not_in_archive(self):
        m = manifest()
        result = self.check(view(m, {}), m, "SAFE")
        self.assertTrue(any("not in archive" in r for r in result["reasons"]))

    def test_unknown_pocket(self):
        m = manifest()
        self.check(view(m, {"resolute": "1:1.0", "noble": "1:0.9"}), m, "UNKNOWN")

    def test_typed_record_rejected(self):
        typed = {"source_package": "demo", "apt_candidate_binary_version": "1:1.0+unity1", "apt_policy_checked": True}
        self.check(typed, manifest(), "UNKNOWN")

    def test_binaries_must_match_manifest(self):
        m = manifest()
        v = view(m, {"resolute": "1:1.0"})
        v["binaries"] = v["binaries"][:1]
        self.check(v, m, "UNKNOWN")

    def test_pre_build_never_safe(self):
        m = manifest()
        ok = self.check(view(m, {"resolute": "1:1.0"}, mode="pockets"), None, "UNKNOWN",
                        pre_build=True, candidate="1:1.0+unity1", source_commit="c0ffee")
        self.assertTrue(any("never SAFE" in r for r in ok["reasons"]))
        self.check(view(m, {"resolute": "1:1.0+unity1"}, mode="pockets"), None, "UNSAFE",
                   pre_build=True, candidate="1:1.0+unity1", source_commit="c0ffee")

    def test_mode_mismatch(self):
        m = manifest()
        self.check(view(m, {"resolute": "1:1.0"}, mode="pockets"), m, "UNKNOWN")


class CompareViewsTest(unittest.TestCase):
    base = {"snapshot": {"name": "s", "list_sha256": "a",
                         "model_release": {"Origin": ". resolute", "Label": ". resolute", "Suite": "resolute", "Codename": "resolute"}},
            "sources_sha256": "src", "preferences": {"ubuntu-pro-esm-apps": "p1"},
            "releases": [{"file": "arch_resolute_InRelease", "Date": "Sat, 26 Sep 2026 18:00:00 UTC"},
                         {"file": "<model>_Release", "model": True, "Date": "Sun, 27 Sep 2026 20:00:00 +0000"}]}
    now = datetime(2026, 9, 27, 21, 0, tzinfo=timezone.utc)

    def fresh(self, **changes):
        v = json.loads(json.dumps(self.base))
        for key, value in changes.items():
            v[key] = value
        return v

    def test_same_or_newer_ok(self):
        f = self.fresh(releases=[{"file": "arch_resolute_InRelease", "Date": "Sun, 27 Sep 2026 13:00:00 UTC"}])
        self.assertIsNone(publish_aptly.compare_views(self.base, f, self.now))

    def test_other_snapshot_content(self):
        f = self.fresh(snapshot={"name": "s", "list_sha256": "b"})
        self.assertIn("package list differs", publish_aptly.compare_views(self.base, f, self.now))

    def test_release_went_backwards(self):
        f = self.fresh(releases=[{"file": "arch_resolute_InRelease", "Date": "Fri, 25 Sep 2026 18:00:00 UTC"}])
        self.assertIn("went backwards", publish_aptly.compare_views(self.base, f, self.now))

    def test_release_missing(self):
        f = self.fresh(releases=[])
        self.assertIn("missing", publish_aptly.compare_views(self.base, f, self.now))

    def test_apt_inputs_changed(self):
        for key, value in (("sources_sha256", "other"), ("preferences", {})):
            with self.subTest(key=key):
                f = self.fresh(**{key: value})
                self.assertIn("apt view inputs", publish_aptly.compare_views(self.base, f, self.now))

    def test_model_release_changed(self):
        snap = dict(self.base["snapshot"], model_release={"Origin": "unity resolute", "Label": "unity resolute",
                                                          "Suite": "resolute", "Codename": "resolute"})
        f = self.fresh(snapshot=snap)
        self.assertIn("Release identity", publish_aptly.compare_views(self.base, f, self.now))

    def test_valid_until_passed(self):
        f = self.fresh(releases=[{"file": "arch_resolute_InRelease", "Date": "Sun, 27 Sep 2026 13:00:00 UTC",
                                  "Valid-Until": "Sun, 27 Sep 2026 14:00:00 UTC"}])
        self.assertIn("expired", publish_aptly.compare_views(self.base, f, self.now))


class PublicationRecordContractTest(unittest.TestCase):
    """What publish_aptly.py writes at the switch is what taskctl.py requires for PUBLISHED."""

    def record(self, evidence):
        return dict({"package": "demo", "candidate_version": "1:1.0+unity1", "snapshot": "s"}, **evidence)

    def test_publisher_record_satisfies_taskctl(self):
        m = manifest()
        fresh_view = view(m, {"resolute": "1:1.0"})
        fresh_result = version_safety.decide(fresh_view, m)
        taskctl.check_switch_time_evidence(self.record(publish_aptly.publication_evidence(fresh_result, fresh_view)))

    def test_old_style_or_unsafe_record_refused(self):
        m = manifest()
        old = {"fresh_apt_policy": {"result": "PASS", "candidate_version": "1:1.0+unity1", "checked_at": "x"}}
        with self.assertRaises(ValueError):
            taskctl.check_switch_time_evidence(self.record(old))
        unsafe_view = view(m, {"resolute": "1:1.0"}, {"demo-bin": "1:2.0"})
        evidence = publish_aptly.publication_evidence(version_safety.decide(unsafe_view, m), unsafe_view)
        with self.assertRaises(ValueError):
            taskctl.check_switch_time_evidence(self.record(evidence))


@unittest.skipUnless(shutil.which("aptly") and shutil.which("apt-ftparchive") and os.geteuid() != 0,
                     "needs aptly, apt-ftparchive and a non-root user")
class AptViewIntegrationTest(unittest.TestCase):
    """apt_view.py against local fixture archives and a scratch aptly snapshot (no network)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def deb(self, directory, name, version, arch):
        root = self.t / f".b-{name}-{version}"
        (root / "DEBIAN").mkdir(parents=True, exist_ok=True)
        (root / "DEBIAN" / "control").write_text(
            f"Package: {name}\nVersion: {version}\nArchitecture: {arch}\nSource: demo\n"
            "Maintainer: t <t@example.com>\nDescription: t\n")
        path = directory / f"{name}_{version.split(':', 1)[-1]}_{arch}.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(path)],
                       check=True, capture_output=True)
        return path

    def archive(self, pockets):
        """A local archive: dists/<pocket>/main/{binary-amd64/Packages,source/Sources} and a Release."""
        arch = self.t / "archive"
        for pocket, (binary_version, source_version) in pockets.items():
            d = arch / "dists" / pocket / "main"
            (d / "binary-amd64").mkdir(parents=True)
            (d / "source").mkdir(parents=True)
            (d / "binary-amd64" / "Packages").write_text(
                f"Package: demo-bin\nVersion: {binary_version}\nArchitecture: amd64\nSource: demo\n")
            (d / "source" / "Sources").write_text(
                f"Package: demo\nBinary: demo-bin\nVersion: {source_version}\nArchitecture: any\n")
            release = subprocess.run(["apt-ftparchive", "-o", f"APT::FTPArchive::Release::Suite={pocket}",
                                      "-o", "APT::FTPArchive::Release::Components=main",
                                      "-o", "APT::FTPArchive::Release::Architectures=amd64 source",
                                      "release", str(arch / "dists" / pocket)], check=True, capture_output=True, text=True)
            (arch / "dists" / pocket / "Release").write_text(release.stdout)
        sources = self.t / "target.sources"
        sources.write_text(f"Types: deb deb-src\nURIs: file:{arch}/\nSuites: {' '.join(pockets)}\n"
                           "Components: main\nTrusted: yes\n")
        return sources

    def snapshot(self, files):
        conf = self.t / "aptly.conf"
        conf.write_text(json.dumps({"rootDir": str(self.t / "aptly"), "gpgDisableSign": True, "gpgDisableVerify": True}))
        indir = self.t / "in"
        indir.mkdir(exist_ok=True)
        a = ["aptly", f"-config={conf}"]
        subprocess.run(a + ["repo", "create", "r"], check=True, capture_output=True)
        subprocess.run(a + ["repo", "add", "r", str(indir)], check=True, capture_output=True)
        subprocess.run(a + ["snapshot", "create", "s", "from", "repo", "r"], check=True, capture_output=True)
        return conf

    def manifest_file(self, entries):
        m = {"package": "demo", "candidate_version": "1:1.0+unity1", "source_commit": "c0ffee",
             "artifacts": [{"file": p.name, "kind": "binary", "package": n, "version": v, "architecture": a}
                           for p, n, v, a in entries]}
        path = self.t / "manifest.json"
        path.write_text(json.dumps(m))
        return path, m

    def apt_view(self, *args):
        prefs = self.t / "prefs"
        prefs.mkdir(exist_ok=True)
        out = self.t / "view.json"
        result = subprocess.run([sys.executable, str(SCRIPTS / "apt_view.py"), "--preferences-dir", str(prefs),
                                 "--write", str(out)] + list(args), capture_output=True, text=True,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        return result, (json.loads(out.read_text()) if out.exists() else None)

    def test_full_view_selects_snapshot_binaries(self):
        sources = self.archive({"resolute": ("1:1.0", "1:1.0"), "resolute-updates": ("1:1.0-0ubuntu0.1", "1:1.0-0ubuntu0.1")})
        indir = self.t / "in"
        indir.mkdir()
        entries = [(self.deb(indir, "demo-bin", "1:1.0+unity1", "amd64"), "demo-bin", "1:1.0+unity1", "amd64"),
                   (self.deb(indir, "demo-data", "1:1.0+unity1", "all"), "demo-data", "1:1.0+unity1", "all")]
        conf = self.snapshot(entries)
        mpath, m = self.manifest_file(entries)
        result, v = self.apt_view("--manifest", str(mpath), "--snapshot", "s", "--aptly-config", str(conf),
                                  "--sources", str(sources))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(v["pockets"], {"resolute": "1:1.0", "resolute-updates": "1:1.0-0ubuntu0.1"})
        self.assertEqual({b["package"]: b["apt_candidate"] for b in v["binaries"]},
                         {"demo-bin": "1:1.0+unity1", "demo-data": "1:1.0+unity1"})
        self.assertEqual(version_safety.decide(v, m)["result"], "SAFE")
        models = [r for r in v["releases"] if r.get("model")]
        self.assertEqual([r["file"] for r in models], ["<model>_Release"])
        self.assertTrue(all("apt-view-" not in r["file"] for r in v["releases"]))
        # two measurements of the same state must compare cleanly (no per-run names)
        result2, v2 = self.apt_view("--manifest", str(mpath), "--snapshot", "s", "--aptly-config", str(conf),
                                    "--sources", str(sources))
        self.assertIsNone(publish_aptly.compare_views(v, v2, datetime.now(timezone.utc)))

    def test_snapshot_older_than_archive_is_unsafe(self):
        sources = self.archive({"resolute": ("1:1.0", "1:1.0"), "resolute-updates": ("1:2.0", "1:2.0")})
        indir = self.t / "in"
        indir.mkdir()
        entries = [(self.deb(indir, "demo-bin", "1:1.0+unity1", "amd64"), "demo-bin", "1:1.0+unity1", "amd64")]
        conf = self.snapshot(entries)
        mpath, m = self.manifest_file(entries)
        result, v = self.apt_view("--manifest", str(mpath), "--snapshot", "s", "--aptly-config", str(conf),
                                  "--sources", str(sources))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(v["binaries"][0]["apt_candidate"], "1:2.0")
        self.assertEqual(version_safety.decide(v, m)["result"], "REPLACES_SECURITY_UPDATE")

    def test_fetch_failure_refuses(self):
        sources = self.t / "broken.sources"
        sources.write_text(f"Types: deb\nURIs: file:{self.t}/missing/\nSuites: resolute\nComponents: main\nTrusted: yes\n")
        result, v = self.apt_view("--source-package", "demo", "--sources", str(sources))
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(v)


if __name__ == "__main__":
    unittest.main()
