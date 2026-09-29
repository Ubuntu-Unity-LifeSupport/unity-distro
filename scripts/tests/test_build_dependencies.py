#!/usr/bin/env python3
"""Tests for scripts/build_dependencies.py (UNITY-20260929-013): the pool
layout, the .buildinfo parser, and the check create_release_gate.py and
publish_aptly.py apply to a manifest's optional build_dependencies.
Run: python3 -m unittest discover -s scripts/tests
"""

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_dependencies", HERE.parent / "build_dependencies.py")
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)


def make_deb(path, package, version, arch="amd64", source=None):
    root = path.parent / f".root-{path.name}"
    (root / "DEBIAN").mkdir(parents=True)
    control = f"Package: {package}\nVersion: {version}\nArchitecture: {arch}\nMaintainer: t <t@example.com>\nDescription: t\n"
    if source:
        control += f"Source: {source}\n"
    (root / "DEBIAN" / "control").write_text(control)
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(path)],
                   check=True, capture_output=True)
    return path


class LayoutTest(unittest.TestCase):
    def test_source_name(self):
        self.assertEqual(bd.source_name("nux (4.0.8-0ubuntu15+unity2)", "libnux-4.0-dev"), "nux")
        self.assertEqual(bd.source_name("nux", "libnux-4.0-dev"), "nux")
        self.assertEqual(bd.source_name(None, "libnux-4.0-dev"), "libnux-4.0-dev")
        self.assertEqual(bd.source_name("  ", "demo"), "demo")

    def test_pool_path(self):
        root = Path("/p")
        self.assertEqual(bd.pool_path(root, "libnux-4.0-dev", "4.0.8-0ubuntu15+unity2", "amd64", "nux"),
                         root / "main/n/nux/libnux-4.0-dev_4.0.8-0ubuntu15+unity2_amd64.deb")
        self.assertEqual(bd.pool_path(root, "libunity-dev", "7.1.4-6+unity1", "amd64", "libunity"),
                         root / "main/libu/libunity/libunity-dev_7.1.4-6+unity1_amd64.deb")
        self.assertEqual(bd.pool_path(root, "calamares-settings-ubuntu-common", "1:26.04.12+unity2", "all",
                                      "calamares-settings-ubuntu"),
                         root / "main/c/calamares-settings-ubuntu/calamares-settings-ubuntu-common_26.04.12+unity2_all.deb")

    def test_installed_build_depends(self):
        text = ("Source: unity\nInstalled-Build-Depends:\n autoconf (= 2.72-3.1ubuntu2),\n"
                " libnux-4.0-dev (= 4.0.8+18.10.20180623-0ubuntu15+unity2),\n libc6:amd64 (= 2.43-2ubuntu2),\n"
                " zlib1g (= 1:1.3.dfsg+really1.3.1-1ubuntu3)\nEnvironment:\n DEB_BUILD_OPTIONS=\"parallel=4\"\n")
        found = bd.installed_build_depends(text)
        self.assertEqual(found[("libnux-4.0-dev", None)], "4.0.8+18.10.20180623-0ubuntu15+unity2")
        self.assertEqual(found[("libc6", "amd64")], "2.43-2ubuntu2")
        self.assertEqual(found[("zlib1g", None)], "1:1.3.dfsg+really1.3.1-1ubuntu3")
        self.assertNotIn(("DEB_BUILD_OPTIONS", None), found)
        with self.assertRaises(ValueError):
            bd.installed_build_depends("Source: unity\n")
        with self.assertRaises(ValueError):
            bd.installed_build_depends("Installed-Build-Depends:\n libfoo (>= 1.0)\n")
        # a substring must not match: libnux-4.0-dev-extra is another package
        self.assertNotIn(("libnux-4.0-dev", None),
                         bd.installed_build_depends("Installed-Build-Depends:\n libnux-4.0-dev-extra (= 1)\n"))


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.pool = self.base / "public" / "pool"
        self.candidate = self.base / "public" / "candidate"
        self.out = self.base / "out"
        pooled = make_deb(self.pool / "main/n/nux/libnux-4.0-dev_4.0.8-0ubuntu15+unity2_amd64.deb",
                          "libnux-4.0-dev", "4.0.8-0ubuntu15+unity2", source="nux")
        self.copy = self.out / "build-dependencies" / pooled.name
        self.copy.parent.mkdir(parents=True)
        self.copy.write_bytes(pooled.read_bytes())
        self.entry = {"file": f"build-dependencies/{pooled.name}", "sha256": hashlib.sha256(pooled.read_bytes()).hexdigest(),
                      "size": pooled.stat().st_size, "package": "libnux-4.0-dev", "version": "4.0.8-0ubuntu15+unity2",
                      "architecture": "amd64", "source": "nux", "given_path": str(pooled),
                      "resolved_path": str(pooled), "in_our_repository_pool": True, "pool_path": str(pooled)}

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, entries):
        return bd.check_entries(entries, self.out, self.pool)

    def test_valid(self):
        self.assertIsNone(self.check([self.entry]))

    def test_manifest_without_key_unchanged(self):
        self.assertIsNone(bd.manifest_error({"schema": 1, "artifacts": []}, self.out, self.pool))
        self.assertIsNone(bd.manifest_error({"build_dependencies": [self.entry]}, self.out, self.pool))
        self.assertIsNotNone(bd.manifest_error({"build_dependencies": []}, self.out, self.pool))

    def test_refused(self):
        cases = {
            "not a list": "x",
            "empty list": [],
            "missing field": [{k: v for k, v in self.entry.items() if k != "source"}],
            "absolute file": [dict(self.entry, file=str(self.copy))],
            "dot-dot file": [dict(self.entry, file="../out/" + self.entry["file"])],
            "missing copy": [dict(self.entry, file="build-dependencies/nothere.deb")],
            "wrong sha256": [dict(self.entry, sha256="0" * 64)],
            "pool_path outside the pool": [dict(self.entry, pool_path=str(self.base / "elsewhere.deb"))],
        }
        for label, entries in cases.items():
            with self.subTest(case=label):
                self.assertIsNotNone(self.check(entries))
        # tampered copy: bytes differ from the recorded sha256
        self.copy.write_bytes(self.copy.read_bytes() + b"x")
        self.assertIn("does not match", self.check([self.entry]))

    def test_not_in_pool(self):
        """Bytes in candidate/ only (unpublished staging) or other bytes in the pool: refused."""
        other = make_deb(self.candidate / "libnux-4.0-common_4.0.8-0ubuntu15+unity2_all.deb",
                         "libnux-4.0-common", "4.0.8-0ubuntu15+unity2", arch="all", source="nux")
        copy = self.out / "build-dependencies" / other.name
        copy.write_bytes(other.read_bytes())
        entry = dict(self.entry, file=f"build-dependencies/{other.name}", package="libnux-4.0-common",
                     architecture="all", sha256=hashlib.sha256(other.read_bytes()).hexdigest())
        entry.pop("pool_path")
        self.assertIn("not in our published pool", self.check([entry]))
        # same name in the pool, different bytes
        pool_other = make_deb(self.pool / "main/n/nux/.x" / other.name, "libnux-4.0-common",
                              "4.0.8-0ubuntu15+unity2", arch="all", source="nux (1)")
        (self.pool / "main/n/nux" / other.name).write_bytes(pool_other.read_bytes())
        self.assertIn("not in our published pool", self.check([entry]))

    def test_recorded_pool_path_not_trusted(self):
        """A recorded pool_path inside the root that is not the package's own
        pool location does not make it pass: the path is recomputed."""
        entry = dict(self.entry, source="notnux")
        self.assertIn("not in our published pool", self.check([entry]))


class ConsumerTest(unittest.TestCase):
    def test_consumers_call_the_check(self):
        """create_release_gate.py and publish_aptly.py both call manifest_error on the build manifest."""
        for name, call in (("create_release_gate.py", "manifest_error(manifest, args.build_manifest.parent)"),
                           ("publish_aptly.py", "manifest_error(manifest, manifest_path.parent)")):
            text = (HERE.parent / name).read_text()
            self.assertIn("from build_dependencies import manifest_error", text, name)
            self.assertIn(call, text, name)


if __name__ == "__main__":
    unittest.main()
