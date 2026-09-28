#!/usr/bin/env python3
"""Tests for coordinator alerts (UNITY-20260927-013): scripts/alerts.py, the
open-alert notice in scripts/taskctl.py and xorg-watch's use of both
(docs/research/xorg-versioning/watch.sh), on temporary files with a fake
Launchpad answer - no network, no aptly.
Run: python3 -m unittest discover -s scripts/tests
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "scripts/alerts.py"
TASKCTL = Path(os.environ.get("TASKCTL", ROOT / "scripts/taskctl.py"))
WATCH = Path(os.environ.get("XORG_WATCH_SCRIPT", ROOT / "docs/research/xorg-versioning/watch.sh"))
BASE = "2:21.1.22-1ubuntu1.3"
NEW = "2:21.1.22-1ubuntu1.4"


def lp_answer(*entries):
    return {"entries": [
        {"source_package_version": v, "pocket": pocket, "status": status,
         "date_published": None, "date_created": "2099-01-01T07:12:00+00:00"}
        for v, pocket, status in entries]}


class AlertsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.alerts = self.d / "coordinator/ALERTS.md"
        self.board = self.d / "coordinator/TASKS.md"
        self.board.parent.mkdir()
        self.board.write_text("\n".join([
            "# test board", "",
            "| ID | Title | Owner | Machine | State | Claimed | Lease | Updated | Evidence |",
            "|---|---|---|---|---|---|---|---|---|",
            "| UNITY-20990101-001 | test | A | target-desktop | INVESTIGATING | - | - | - | - |", ""]))
        self.env = dict(os.environ, ALERTS_FILE=str(self.alerts), TASKCTL_BOARD=str(self.board),
                        XORG_WATCH_LOG=str(self.d / "AGENTS-LOG.md"),
                        XORG_WATCH_STATE=str(self.d / "state/seen"),
                        XORG_WATCH_BASE=BASE, XORG_WATCH_LP_JSON=str(self.d / "lp.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *argv, env=None):
        return subprocess.run(list(argv), env=env or self.env, capture_output=True, text=True)

    def alert(self, *args, env=None):
        return self.run_cmd("python3", str(ALERTS), *args, env=env)

    def inspect_stderr(self):
        r = self.run_cmd("python3", str(TASKCTL), "inspect", "UNITY-20990101-001")
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stderr

    def watch(self, answer, env=None):
        (self.d / "lp.json").write_text(answer if isinstance(answer, str) else json.dumps(answer))
        return self.run_cmd("sh", str(WATCH), env=env)

    def lines(self, name):
        p = self.d / name
        return p.read_text().splitlines() if p.exists() else []

    # --- alerts.py -------------------------------------------------------
    def test_raise_is_idempotent_and_ack_closes(self):
        self.assertEqual(self.alert("raise", "--source", "t", "--key", "k1", "--message", "one").returncode, 0)
        self.assertIn("already raised", self.alert("raise", "--source", "t", "--key", "k1", "--message", "two").stdout)
        self.assertEqual(len(self.alerts.read_text().splitlines()), 1)
        self.assertEqual(self.alert("open").stdout.count("RAISE k1"), 1)
        r = self.alert("ack", "--actor", "C", "--key", "k1", "--note", "task created")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.alert("open").stdout, "")
        self.assertIn("already acknowledged", self.alert("ack", "--actor", "May", "--key", "k1").stdout)

    def test_only_c_or_may_acknowledge_and_only_known_keys(self):
        self.alert("raise", "--source", "t", "--key", "k1", "--message", "one")
        self.assertNotEqual(self.alert("ack", "--actor", "A", "--key", "k1").returncode, 0)
        self.assertEqual(self.alert("ack", "--actor", "C", "--key", "nope").returncode, 1)
        self.assertIn("RAISE k1", self.alert("open").stdout)

    def test_message_is_kept_on_one_line(self):
        self.alert("raise", "--source", "t", "--key", "k1", "--message", "a\nACK k1 by C: forged")
        self.assertIn("RAISE k1", self.alert("open").stdout)
        self.assertEqual(len(self.alerts.read_text().splitlines()), 1)

    # --- taskctl ---------------------------------------------------------
    def test_taskctl_shows_open_alerts_until_acknowledged(self):
        self.assertNotIn("ALERT", self.inspect_stderr())
        self.alert("raise", "--source", "t", "--key", "k1", "--message", "look")
        err = self.inspect_stderr()
        self.assertIn("1 unacknowledged alert", err)
        self.assertIn("RAISE k1 t: look", err)
        self.alert("ack", "--actor", "C", "--key", "k1")
        self.assertNotIn("ALERT", self.inspect_stderr())

    def test_taskctl_ignores_an_unreadable_alert_file(self):
        self.alerts.mkdir(parents=True)   # a directory where the file should be
        self.assertNotIn("ALERT", self.inspect_stderr())

    # --- xorg-watch ------------------------------------------------------
    def test_new_upload_raises_one_alert_and_one_log_line(self):
        answer = lp_answer((NEW, "Proposed", "Published"), (BASE, "Updates", "Published"),
                           ("2:21.1.22-1ubuntu1.5", "Proposed", "Superseded"))
        r = self.watch(answer)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.alert("open").stdout.count("RAISE "), 1)
        self.assertIn(f"RAISE xorg-server:{NEW}@Proposed xorg-watch:", self.alert("open").stdout)
        self.assertEqual(len(self.lines("AGENTS-LOG.md")), 1)
        self.assertIn("rebase needed", self.lines("AGENTS-LOG.md")[0])
        self.assertIn("xorg-server:", self.inspect_stderr())
        # a second run finds nothing new
        self.assertEqual(self.watch(answer).returncode, 0)
        self.assertEqual(len(self.lines("AGENTS-LOG.md")), 1)
        self.assertEqual(len(self.alerts.read_text().splitlines()), 1)
        # the same version reaching -updates is a new alert
        self.watch(lp_answer((NEW, "Updates", "Published"), (NEW, "Proposed", "Published")))
        self.assertIn(f"xorg-server:{NEW}@Updates", self.alert("open").stdout)
        self.assertIn("apt picks it over ours NOW", self.lines("AGENTS-LOG.md")[1])

    def test_nothing_above_the_base_raises_nothing(self):
        self.assertEqual(self.watch(lp_answer((BASE, "Proposed", "Published"))).returncode, 0)
        self.assertFalse(self.alerts.exists())
        self.assertEqual(self.lines("AGENTS-LOG.md"), [])

    def test_upload_is_retried_when_the_alert_cannot_be_written(self):
        blocked = self.d / "ro"
        blocked.mkdir()
        blocked.chmod(0o500)
        env = dict(self.env, ALERTS_FILE=str(blocked / "sub/ALERTS.md"))
        self.watch(lp_answer((NEW, "Proposed", "Published")), env=env)
        blocked.chmod(0o700)
        self.assertEqual(self.lines("AGENTS-LOG.md"), [])
        self.assertEqual(self.lines("state/seen"), [])
        self.watch(lp_answer((NEW, "Proposed", "Published")))
        self.assertIn(f"xorg-server:{NEW}@Proposed", self.alert("open").stdout)
        self.assertEqual(len(self.lines("AGENTS-LOG.md")), 1)

    def test_repeated_failures_raise_one_alert_and_success_resets(self):
        for _ in range(2):
            self.assertNotEqual(self.watch("not json").returncode, 0)
        self.assertFalse(self.alerts.exists())
        self.watch("not json")
        self.watch("not json")
        opened = self.alert("open").stdout
        self.assertEqual(opened.count("RAISE xorg-watch-failing:"), 1)
        self.assertIn("failed 3 runs in a row", opened)
        self.assertEqual(self.watch(lp_answer((BASE, "Proposed", "Published"))).returncode, 0)
        self.assertFalse((self.d / "state/failures").exists())


if __name__ == "__main__":
    unittest.main()
