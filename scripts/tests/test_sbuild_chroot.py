#!/usr/bin/env python3
"""Tests for scripts/sbuild_chroot.py (UNITY-20260929-016): the tarball check
build_sbuild.py runs before sbuild and the log check it runs after.
Run: python3 -m unittest discover -s scripts/tests
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import sbuild_chroot  # noqa: E402
from chroot_fixtures import make_chroot, stamp_days_ago  # noqa: E402

# Real sbuild lines (UNITY-20260927-040 on the tarball; UNITY-20260927-041 on
# sbuild's on-demand chroot).
TARBALL_LOG = """I: Unpacking {tarball} to /var/tmp/sbuild-claude/sbuild-unshare-W_y9bj...
Get:1 file:/build/reproducible-path/resolver-SzfLIV/apt_archive ./ InRelease
Get:2 copy:/build/reproducible-path/resolver-N3cJkD/apt_archive ./ Release [615 B]
Get:5 https://snapshot.ubuntu.com/ubuntu/{stamp} resolute InRelease [136 kB]
Get:6 https://snapshot.ubuntu.com/ubuntu/{stamp} resolute-updates InRelease [137 kB]
Get:9 https://snapshot.ubuntu.com/ubuntu/{stamp} resolute/universe amd64 Packages [16.0 MB]
Hit:3 https://snapshot.ubuntu.com/ubuntu/{stamp} resolute-security InRelease
Unpacking mount (2.41-4ubuntu4) ...
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
"""
ON_DEMAND_LOG = """I: Existing chroot tarball is too old (7.01 >= 7.00 days):
I: Creating chroot on-demand by running:
mmdebstrap --variant=buildd --arch=amd64 --skip=output/mknod --format=tar resolute - --components=main,universe
I: Unpacking tarball from STDIN to /var/tmp/sbuild-claude/sbuild-unshare-o5ymyW...
Get:1 http://archive.ubuntu.com/ubuntu resolute InRelease [136 kB]
"""


class TarballTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, tarball, allow_old=False):
        return sbuild_chroot.check_tarball(tarball, "resolute", "amd64", allow_old)

    def test_valid(self):
        tarball = make_chroot(self.dir)
        info, error = self.check(tarball)
        self.assertIsNone(error)
        self.assertEqual(info["sources"][0].split()[1].rsplit("/", 1)[1], info["snapshot"])
        self.assertEqual(len(info["sources"]), 3)
        self.assertFalse(info["allow_old_chroot"])

    def test_refused(self):
        stamp = stamp_days_ago(1)
        other = sbuild_chroot.sources_lines("resolute", stamp)
        cases = {
            "multiverse": lambda: make_chroot(self.dir, stamp=stamp, lines=[l + " multiverse" for l in other]),
            "proposed": lambda: make_chroot(self.dir, stamp=stamp, lines=other + [other[0].replace(" resolute ", " resolute-proposed ")]),
            "live mirror": lambda: make_chroot(self.dir, stamp=stamp, lines=[l.replace(f"snapshot.ubuntu.com/ubuntu/{stamp}", "de.archive.ubuntu.com/ubuntu") for l in other]),
            "another snapshot": lambda: make_chroot(self.dir, stamp=stamp, lines=sbuild_chroot.sources_lines("resolute", stamp_days_ago(2))),
            "sources.list.d file": lambda: make_chroot(self.dir, stamp=stamp, extra_files=["etc/apt/sources.list.d/x.list"]),
            "no sidecar": lambda: make_chroot(self.dir, stamp=stamp, write_sidecar=False),
            "sidecar sha256": lambda: make_chroot(self.dir, stamp=stamp, sidecar_changes={"sha256": "0" * 64}),
            "sidecar series": lambda: make_chroot(self.dir, stamp=stamp, sidecar_changes={"series": "noble"}),
            "sidecar sources": lambda: make_chroot(self.dir, stamp=stamp, sidecar_changes={"sources": other[:2]}),
            "old snapshot": lambda: make_chroot(self.dir, stamp=stamp_days_ago(8)),
        }
        for label, make in cases.items():
            with self.subTest(case=label):
                self.tearDown(); self.setUp()
                info, error = self.check(make())
                self.assertIsNone(info)
                self.assertTrue(error)

    def test_future_snapshot_refused(self):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%dT%H%M%SZ")
        info, error = self.check(make_chroot(self.dir, stamp=future), allow_old=True)
        self.assertIsNone(info)
        self.assertIn("future", error)

    def test_old_snapshot_allowed_and_recorded(self):
        info, error = self.check(make_chroot(self.dir, stamp=stamp_days_ago(8)), allow_old=True)
        self.assertIsNone(error)
        self.assertTrue(info["allow_old_chroot"])
        self.assertTrue(info["older_than_max_age"])

    def test_path_rules(self):
        tarball = make_chroot(self.dir)
        link = self.dir / "link.tar.zst"
        link.symlink_to(tarball)
        self.assertIsNotNone(self.check(link)[1])
        self.assertIsNotNone(self.check(Path(tarball.name))[1])  # relative
        renamed = self.dir / "resolute-amd64.tar.zst"
        tarball.rename(renamed)
        self.assertIsNotNone(self.check(renamed)[1])

    def test_current_tarball(self):
        older = make_chroot(self.dir, stamp=stamp_days_ago(3))
        newer = make_chroot(self.dir, stamp=stamp_days_ago(1))
        make_chroot(self.dir, stamp=stamp_days_ago(0.5), write_sidecar=False)  # no sidecar: ignored
        self.assertEqual(sbuild_chroot.current_tarball("resolute", "amd64", self.dir), newer)
        self.assertNotEqual(older, newer)
        self.assertIsNone(sbuild_chroot.current_tarball("noble", "amd64", self.dir))


class LogTest(unittest.TestCase):
    tarball = Path("/c/resolute-amd64-20260929T000000Z.tar.zst")
    stamp = "20260929T000000Z"

    def check(self, text):
        return sbuild_chroot.check_log(text, self.tarball, self.stamp, "resolute")

    def good(self):
        return TARBALL_LOG.format(tarball=self.tarball, stamp=self.stamp)

    def test_tarball_log_accepted(self):
        fetched, error = self.check(self.good())
        self.assertIsNone(error)
        self.assertEqual(len(fetched), 3)  # the three InRelease lines, Hit included

    def test_on_demand_log_refused(self):
        self.assertIn("on-demand", self.check(ON_DEMAND_LOG)[1])
        # even with this tarball's line present
        self.assertIsNotNone(self.check(self.good() + ON_DEMAND_LOG)[1])

    def test_refused(self):
        good = self.good()
        cases = {
            "no unpack line": good.replace(f"I: Unpacking {self.tarball} to", "I: something"),
            "dpkg Unpacking only": "\n".join(l for l in good.splitlines() if not l.startswith("I: Unpacking")),
            "another tarball": good.replace(str(self.tarball), "/c/resolute-amd64-20260101T000000Z.tar.zst"),
            "tarball path as a prefix only": good.replace(f"{self.tarball} to", f"{self.tarball}.old to"),
            "foreign Get": good + "Get:7 http://de.archive.ubuntu.com/ubuntu resolute InRelease [136 kB]\n",
            "foreign Hit": good + "Hit:8 http://security.ubuntu.com/ubuntu resolute-security InRelease\n",
            "other snapshot": good + "Get:7 https://snapshot.ubuntu.com/ubuntu/20260101T000000Z resolute InRelease\n",
            "snapshot prefix trick": good + f"Get:7 https://snapshot.ubuntu.com/ubuntu/{self.stamp}.evil resolute InRelease\n",
            "creating tarball": good + "I: Creating new chroot tarball:\n",
            # Verifier round 1: a local repository from the user's sbuild config
            "local file repository": good + "Get:3 file:/home/claude/evilrepo ./ InRelease\n",
            "local copy repository": good + "Get:3 copy:/tmp/repo ./ Release [615 B]\n",
            "resolver path trick": good + "Get:3 file:/build/reproducible-path/resolver-ab/apt_archive2 ./ InRelease\n",
            "resolver path traversal": good + "Get:3 file:/build/reproducible-path/resolver-ab/../../../home ./ InRelease\n",
            # no InRelease from the snapshot for one pocket (e.g. apt_update off)
            "security pocket missing": "\n".join(l for l in good.splitlines() if "resolute-security" not in l),
            "no snapshot fetch at all": "\n".join(l for l in good.splitlines() if "snapshot.ubuntu.com" not in l),
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                self.assertIsNotNone(self.check(text)[1])


if __name__ == "__main__":
    unittest.main()
