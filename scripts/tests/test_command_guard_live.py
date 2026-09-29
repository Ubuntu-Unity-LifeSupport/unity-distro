#!/usr/bin/env python3
"""Tests for the live-phase allowance in .claude/hooks/command_guard.py
(UNITY-20260929-008).

The hook module is imported, and its list, pinned aptly config, coordinator
directory, marker, log and home directory are pointed at a temporary
directory. Every check runs against real files; nothing touches /srv/aptly,
~/coordinator or aptly. Commands are strings passed to inspect(); nothing is
executed. Run: python3 -m unittest discover -s scripts/tests
"""

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "command_guard.py"
REAL_LIST = HOOK.with_name("live-commands.json")
APTLY = "/usr/bin/aptly"
SESSION = "11111111-2222-3333-4444-555555555555"
P = "publ" + "ish"  # the word, kept out of this file's plain text
KEY = "-gpg-key=7BF3F77FC27B152C"
SNAP = "unity-resolute-20260927-047"
TAILS = [
    f"snapshot -distribution=resolute -architectures=amd64 {KEY} -batch {SNAP} candidate",
    "show resolute candidate",
    "drop resolute",
    f"snapshot -distribution=resolute -architectures=amd64 {KEY} -batch {SNAP}",
    "show resolute",
    f"repo -distribution=resolute -architectures=amd64 {KEY} -batch unity-resolute",
    "list",
    "drop resolute candidate",
]
CONFIG = {"rootDir": "/srv/aptly", "downloadConcurrency": 4, "architectures": ["amd64"],
          "gpgDisableSign": False, "gpgDisableVerify": False, "FileSystemPublishEndpoints": {}}


def load_hook():
    spec = importlib.util.spec_from_file_location("command_guard_live", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stamp(delta):
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@unittest.skipUnless(os.path.exists(APTLY), "aptly is not installed")
class LiveAllowanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        os.chmod(base, 0o700)
        self.home = base / "home"
        self.coord = base / "coordinator"
        self.home.mkdir(mode=0o700)
        self.coord.mkdir(mode=0o700)
        (self.home / ".claude" / "shell-snapshots").mkdir(parents=True)
        self.hook = h = load_hook()
        self.config = self.home / ".aptly.conf"
        self.list = base / "live-commands.json"
        h.REHEARSAL_COORDINATOR = str(self.coord)
        h.REHEARSAL_MARKER = str(self.coord / "rehearsal-authorization.json")
        h.REHEARSAL_LOG = str(self.coord / "rehearsal-log.jsonl")
        h.LIVE_COMMANDS = str(self.list)
        h.LIVE_CONFIG = str(self.config)
        h.LIVE_MARKER = str(self.coord / "live-authorization.json")
        h.LIVE_LOG = str(self.coord / "live-log.jsonl")
        h.LIVE_HOME = str(self.home)
        h.LIVE_PREFIX = f"{APTLY} -config={self.config} {P} "
        self.commands = [h.LIVE_PREFIX + t for t in TAILS]
        self.write_config(CONFIG)
        self.write_list()
        self.write_marker()
        env = mock.patch.dict(os.environ, {}, clear=False)
        env.start()
        os.environ.pop("BASH_ENV", None)
        self.addCleanup(env.stop)

    def tearDown(self):
        self.tmp.cleanup()

    # --- fixtures ---------------------------------------------------------
    def write_config(self, config, mode=0o600):
        self.config.write_text(json.dumps(config, indent=2) + "\n")
        os.chmod(self.config, mode)

    def write_list(self, **over):
        listing = {"schema": 1, "task_id": "UNITY-20260927-047", "root": "/srv/aptly",
                   "aptly_conf_sha256": sha(self.config), "commands": self.commands}
        listing.update(over)
        self.list.write_text(json.dumps(listing, indent=2) + "\n")
        os.chmod(self.list, 0o664)  # as git checks it out

    def marker_fields(self, **over):
        fields = {"schema": 1, "kind": "live-" + P, "task_id": "UNITY-20260927-047", "root": "/srv/aptly",
                  "authorized_by": "May", "recorded_by": "C", "not_before": stamp(timedelta(minutes=-5)),
                  "not_after": stamp(timedelta(hours=2)), "reference": "May GO; L0 record logs/44",
                  "session_id": SESSION, "commands_sha256": sha(self.list)}
        fields.update(over)
        return fields

    def write_marker(self, path=None, **over):
        path = Path(path or self.hook.LIVE_MARKER)
        fields = {k: v for k, v in self.marker_fields(**over).items() if v is not None}
        path.write_text(json.dumps(fields) + "\n")
        os.chmod(path, 0o600)

    def log_lines(self):
        path = Path(self.hook.LIVE_LOG)
        return path.read_text().splitlines() if path.exists() else []

    def allowed(self, command, session=SESSION, tool="Bash", background=False):
        return self.hook.inspect(command, session, tool, background)

    def assert_denied(self, command, text, **kw):
        message = self.allowed(command, **kw)
        self.assertIsNotNone(message, command)
        self.assertIn(text, message)
        self.assertEqual(self.log_lines(), [])

    # --- allowed ------------------------------------------------------------
    def test_every_listed_command_is_admitted_and_logged_once(self):
        for i, command in enumerate(self.commands, 1):
            self.assertIsNone(self.allowed(command), command)
            lines = self.log_lines()
            self.assertEqual(len(lines), i)
            entry = json.loads(lines[-1])
            self.assertEqual((entry["event"], entry["command"], entry["session_id"], entry["tool_name"]),
                             ("admitted", command, SESSION, "Bash"))
            self.assertEqual(entry["commands_sha256"], sha(self.list))
            self.assertEqual(entry["marker_sha256"], sha(self.hook.LIVE_MARKER))

    def test_real_list_is_valid_and_matches_the_phase_l_plan(self):
        listing = json.loads(REAL_LIST.read_text())
        self.assertEqual(listing["task_id"], "UNITY-20260927-047")
        self.assertEqual(listing["root"], "/srv/aptly")
        prefix = f"{APTLY} -config=/home/claude/.aptly.conf {P} "
        self.assertEqual(listing["commands"], [prefix + t for t in TAILS])
        self.assertEqual(json.loads(REAL_LIST.read_text(), object_pairs_hook=dict).keys(),
                         {"schema", "task_id", "root", "aptly_conf_sha256", "commands"})

    # --- the command string ---------------------------------------------------
    def test_deviations_of_the_string_are_denied(self):
        c = self.commands[2]  # drop resolute
        for bad in [c + " ", c + "\n", c + "\r\n", c.replace("drop ", "drop\t"), c.replace("drop ", "drop  "),
                    c + " -force-drop", c.replace("resolute", "resolutе"), c + ";true", c + " && true",
                    c + " > /tmp/x", self.commands[0].replace(SNAP, SNAP + "b"),
                    self.commands[0].replace(" -batch", ""), c.replace("drop resolute", "drop resolute x")]:
            self.assert_denied(bad, "not an exact entry")

    def test_near_misses_outside_the_prefix_are_denied_by_the_other_paths(self):
        c = self.commands[2]
        for bad in ["env " + c, "sudo " + c, " " + c, c.replace(APTLY, "aptly", 1),
                    c.replace(" ", "\t", 1), c.replace(" ", "  ", 1),
                    c.replace("-config=", "--config=", 1), c.replace(str(self.config), "/tmp/other.conf")]:
            message = self.allowed(bad)
            self.assertIsNotNone(message, bad)
            self.assertNotIn("aptly live command not allowed", message)
        self.assertEqual(self.log_lines(), [])

    # --- tool ---------------------------------------------------------------
    def test_only_a_foreground_bash_call(self):
        self.assert_denied(self.commands[2], "foreground Bash", tool="Monitor")
        self.assert_denied(self.commands[2], "foreground Bash", background=True)
        self.assert_denied(self.commands[2], "foreground Bash", tool=None)

    # --- marker -------------------------------------------------------------
    def test_marker_deviations_are_denied(self):
        cases = [
            ({"session_id": "other"}, "another session"),
            ({"kind": "rehearsal"}, "kind must be"),
            ({"task_id": "UNITY-20260927-021"}, "for this task"),
            ({"root": "/var/tmp/aptly-rehearsal"}, "for this task"),
            ({"authorized_by": "C"}, "for this task"),
            ({"recorded_by": "B"}, "for this task"),
            ({"commands_sha256": "0" * 64}, "another command list"),
            ({"commands_sha256": None}, "must have exactly"),
            ({"extra": "x"}, "must have exactly"),
            ({"schema": 2}, "unknown schema"),
            ({"not_before": stamp(timedelta(hours=-3)), "not_after": stamp(timedelta(minutes=-1))}, "not valid now"),
            ({"not_before": stamp(timedelta(minutes=5))}, "not valid now"),
            ({"not_before": stamp(timedelta(hours=-1)), "not_after": stamp(timedelta(hours=6))}, "at most 6 hours"),
            ({"not_after": "2026-09-29 12:00:00"}, "YYYY-MM-DD"),
        ]
        for over, text in cases:
            with self.subTest(over=over):
                self.write_marker(**over)
                self.assert_denied(self.commands[2], text)

    def test_no_marker(self):
        os.unlink(self.hook.LIVE_MARKER)
        self.assert_denied(self.commands[2], "no live authorization")

    def test_rehearsal_marker_does_not_count_for_live(self):
        os.unlink(self.hook.LIVE_MARKER)
        rehearsal = {k: v for k, v in self.marker_fields().items() if k not in ("kind", "commands_sha256")}
        Path(self.hook.REHEARSAL_MARKER).write_text(json.dumps(rehearsal))
        os.chmod(self.hook.REHEARSAL_MARKER, 0o600)
        self.assert_denied(self.commands[2], "no live authorization")
        # the rehearsal fields at the live path: wrong key set
        self.write_marker(kind=None, commands_sha256=None)
        self.assert_denied(self.commands[2], "must have exactly")

    def test_live_marker_does_not_count_for_the_rehearsal(self):
        self.write_marker(path=self.hook.REHEARSAL_MARKER)
        with self.assertRaises(self.hook.RehearsalDenied) as denied:
            self.hook._check_marker(SESSION)
        self.assertIn("must have exactly", str(denied.exception))

    def test_marker_link_and_coordinator_permissions(self):
        target = Path(self.tmp.name) / "elsewhere.json"
        os.replace(self.hook.LIVE_MARKER, target)
        os.symlink(target, self.hook.LIVE_MARKER)
        self.assert_denied(self.commands[2], "must not resolve elsewhere")
        os.unlink(self.hook.LIVE_MARKER)
        self.write_marker()
        os.chmod(self.coord, 0o770)
        self.assert_denied(self.commands[2], "not writable by group")

    # --- list ---------------------------------------------------------------
    def test_list_edited_after_the_marker(self):
        self.write_list(commands=self.commands + [self.hook.LIVE_PREFIX + "drop resolute x"])
        self.assert_denied(self.commands[2], "another command list")

    def test_malformed_lists(self):
        rehearsal_form = f"{APTLY} -config=/var/tmp/aptly-rehearsal/aptly.conf {P} list"
        for over in [{"commands": self.commands + [self.commands[0]]},
                     {"commands": self.commands + ["echo " + self.commands[0]]},
                     {"commands": self.commands + [rehearsal_form]},
                     {"commands": self.commands + [self.hook.LIVE_PREFIX + "list 'x'"]},
                     {"commands": []}, {"root": "/var/tmp/aptly-rehearsal"}, {"schema": 2},
                     {"aptly_conf_sha256": "x"}, {"extra": 1}]:
            with self.subTest(over=list(over)):
                self.write_list(**over)
                self.write_marker()
                self.assert_denied(self.commands[2], "live command list")

    def test_list_must_not_be_a_link(self):
        target = Path(self.tmp.name) / "list-elsewhere.json"
        os.replace(self.list, target)
        os.symlink(target, self.list)
        self.assert_denied(self.commands[2], "regular file, not a link")

    # --- pinned config ------------------------------------------------------
    def test_config_changed_or_not_private(self):
        self.write_config(dict(CONFIG, downloadConcurrency=5))
        self.assert_denied(self.commands[2], "differs from the reviewed one")
        self.write_config(CONFIG, mode=0o664)
        self.assert_denied(self.commands[2], "not writable by group")

    def test_config_content_is_checked_too(self):
        for bad, text in [(dict(CONFIG, rootDir="/tmp/x"), "rootDir must be"),
                          (dict(CONFIG, S3PublishEndpoints={"x": {}}), "must not have S3"),
                          (dict(CONFIG, FileSystemPublishEndpoints={"x": {"rootDir": "/tmp"}}), "must not have File"),
                          (dict(CONFIG, databaseBackend={"type": "leveldb"}), "must not set")]:
            with self.subTest(text=text):
                self.write_config(bad)
                self.write_list()
                self.write_marker()
                self.assert_denied(self.commands[2], text)

    # --- shell shadowing (best effort) ---------------------------------------
    def test_shadowing_in_rc_or_snapshot_is_refused(self):
        snap = self.home / ".claude" / "shell-snapshots" / "snapshot-bash-1.sh"
        for text in ["function /usr/bin/aptly { echo x; }\n", "aptly () { :; }\n",
                     # the form Claude Code writes into a shell snapshot (Verifier round 1)
                     "eval $'/usr/bin/aptly () \\n{ \\n    echo x\\n}' > /dev/null 2>&1\n",
                     "eval $'aptly () \\n{ \\n    :\\n}' > /dev/null 2>&1\n",
                     "export BASH_FUNC_/usr/bin/aptly%%='() {  echo x\n}'\n",
                     "alias aptly=true\n", "export BASH_ENV=/tmp/x\n", "trap 'echo' DEBUG\n",
                     "export LD_PRELOAD=/tmp/x.so\n", "export LD_LIBRARY_PATH=/tmp\n", "export LD_AUDIT=/tmp/a.so\n"]:
            with self.subTest(text=text):
                snap.write_text("# snapshot\n" + text)
                self.assert_denied(self.commands[2], "defines an aptly function")
        # a real-format snapshot function that does not involve aptly passes
        snap.write_text("eval $'gawkpath_default () \\n{ \\n    unset AWKPATH\\n}' > /dev/null 2>&1\n")
        self.assertIsNone(self.allowed(self.commands[2]))
        Path(self.hook.LIVE_LOG).unlink()
        snap.write_text("# a clean snapshot mentioning nothing\n")
        (self.home / ".bashrc").write_text("alias ll='ls -l'\nfunction /usr/bin/aptly { :; }\n")
        self.assert_denied(self.commands[2], "defines an aptly function")

    def test_shadowing_variables_in_the_environment(self):
        for name in ("BASH_ENV", "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT"):
            with self.subTest(name=name):
                os.environ[name] = "/tmp/x"
                try:
                    self.assert_denied(self.commands[2], f"{name} is set")
                finally:
                    del os.environ[name]

    def test_the_real_home_has_no_shadowing(self):
        # the installed profile and snapshots of this builder must not trip the scan
        self.hook.LIVE_HOME = "/home/claude"
        if os.path.isdir("/home/claude"):
            self.hook._check_live_shell()

    # --- log ----------------------------------------------------------------
    def test_log_must_be_a_private_regular_file(self):
        target = Path(self.tmp.name) / "log-elsewhere"
        target.write_text("")
        os.symlink(target, self.hook.LIVE_LOG)
        self.assertIsNotNone(self.allowed(self.commands[2]))
        self.assertEqual(target.read_text(), "")
        os.unlink(self.hook.LIVE_LOG)
        Path(self.hook.LIVE_LOG).write_text("")
        os.chmod(self.hook.LIVE_LOG, 0o664)
        message = self.allowed(self.commands[2])
        self.assertIn("not writable by group", message)

    def test_failed_log_write_denies(self):
        with mock.patch.object(self.hook.os, "write", side_effect=OSError("disk full")):
            message = self.allowed(self.commands[2])
        self.assertIsNotNone(message)
        self.assertIn("disk full", message)

    # --- the rest of the guard is unchanged ---------------------------------
    def test_rehearsal_still_allowed_while_a_live_marker_exists(self):
        root = Path(self.tmp.name) / "aptly-rehearsal"
        root.mkdir(mode=0o700)
        h = self.hook
        h.REHEARSAL_ROOT = str(root)
        (root / "aptly.conf").write_text(json.dumps({"rootDir": str(root / "r")}))
        os.chmod(root / "aptly.conf", 0o600)
        rehearsal = {k: v for k, v in self.marker_fields(root=str(root)).items()
                     if k not in ("kind", "commands_sha256")}
        Path(h.REHEARSAL_MARKER).write_text(json.dumps(rehearsal))
        os.chmod(h.REHEARSAL_MARKER, 0o600)
        with mock.patch.object(h, "MOUNTINFO", os.devnull):
            self.assertIsNone(h.inspect(f"{APTLY} -config={root}/aptly.conf {P} list", SESSION))
        self.assertEqual(self.log_lines(), [])

    def test_main_end_to_end(self):
        def run(payload):
            out = io.StringIO()
            with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                    mock.patch.object(sys, "stderr", out):
                return self.hook.main(), out.getvalue()
        base = {"session_id": SESSION, "hook_event_name": "PreToolUse"}
        rc, _ = run(dict(base, tool_name="Bash", tool_input={"command": self.commands[4]}))
        self.assertEqual(rc, 0)
        rc, err = run(dict(base, tool_name="Bash", tool_input={"command": self.commands[4], "run_in_background": True}))
        self.assertEqual(rc, 2)
        self.assertIn("foreground Bash", err)
        rc, err = run(dict(base, tool_name="Monitor", tool_input={"command": self.commands[4]}))
        self.assertEqual(rc, 2)
        # a truthy non-boolean counts as background too
        rc, err = run(dict(base, tool_name="Bash", tool_input={"command": self.commands[4], "run_in_background": "yes"}))
        self.assertEqual(rc, 2)
        self.assertEqual(len(self.log_lines()), 1)

    def test_without_the_allowance_every_listed_string_is_denied(self):
        os.unlink(self.hook.LIVE_MARKER)
        for command in self.commands:
            self.assertIsNotNone(self.allowed(command))


if __name__ == "__main__":
    unittest.main()
