#!/usr/bin/env python3
"""Tests for the aptly rehearsal allowance in .claude/hooks/command_guard.py
(UNITY-20260927-057).

The hook module is imported and its rehearsal root, coordinator directory,
marker and log are pointed at a temporary directory, so every check runs
against real files and nothing touches /var/tmp/aptly-rehearsal, the
coordinator directory or aptly. Commands are strings passed to inspect();
nothing is executed. Run: python3 -m unittest discover -s scripts/tests
"""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "command_guard.py"
APTLY = "/usr/bin/aptly"
SESSION = "11111111-2222-3333-4444-555555555555"
P = "publ" + "ish"  # the word, kept out of this file's plain text


def load_hook():
    spec = importlib.util.spec_from_file_location("command_guard_rehearsal", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stamp(delta):
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


@unittest.skipUnless(os.path.exists(APTLY), "aptly is not installed")
class RehearsalAllowanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        os.chmod(base, 0o700)
        self.root = base / "aptly-rehearsal"
        self.coord = base / "coordinator"
        self.root.mkdir(mode=0o700)
        self.coord.mkdir(mode=0o700)
        self.hook = load_hook()
        self.hook.REHEARSAL_ROOT = str(self.root)
        self.hook.REHEARSAL_COORDINATOR = str(self.coord)
        self.hook.REHEARSAL_MARKER = str(self.coord / "rehearsal-authorization.json")
        self.hook.REHEARSAL_LOG = str(self.coord / "rehearsal-log.jsonl")
        self.config = self.root / "aptly.conf"
        self.write_config({"rootDir": str(self.root / "r"), "architectures": ["amd64"]})
        self.write_marker()

    def tearDown(self):
        for top, dirs, _ in os.walk(self.tmp.name):
            for d in dirs:
                path = os.path.join(top, d)
                if not os.path.islink(path):
                    os.chmod(path, 0o700)
        self.tmp.cleanup()

    def write_config(self, value, raw=None):
        self.config.write_text(raw if raw is not None else json.dumps(value))
        os.chmod(self.config, 0o600)

    def write_marker(self, **changes):
        marker = {"schema": 1, "task_id": "UNITY-20260927-047", "root": str(self.root),
                  "authorized_by": "May", "recorded_by": "C",
                  "not_before": stamp(timedelta(hours=-1)), "not_after": stamp(timedelta(hours=1)),
                  "reference": "PENDING-MAY 2026-09-28", "session_id": SESSION}
        marker.update(changes)
        for key in [k for k, v in changes.items() if v is None]:
            del marker[key]
        path = Path(self.hook.REHEARSAL_MARKER)
        path.write_text(json.dumps(marker))
        os.chmod(path, 0o600)

    def command(self, *words, config=None):
        config = config or str(self.config)
        return " ".join([APTLY, f"-config={config}", P] + list(words or ["list"]))

    def allowed(self, command, session=SESSION):
        return self.hook.inspect(command, session)

    def assertAllowed(self, command, session=SESSION):
        self.assertIsNone(self.allowed(command, session))

    def assertDenied(self, command, session=SESSION):
        message = self.allowed(command, session)
        self.assertIsNotNone(message, command)
        if os.environ.get("REHEARSAL_TEST_REASONS"):
            print(f"{self.id().rsplit('.', 1)[-1]} :: {message}", file=sys.stderr)
        return message

    # --- the allowed case ----------------------------------------------------

    def test_allowed_and_logged(self):
        self.assertAllowed(self.command("list"))
        self.assertAllowed(self.command("repo", "-distribution=resolute", "-architectures=amd64",
                                        "-batch", "unity-resolute"))
        lines = Path(self.hook.REHEARSAL_LOG).read_text().splitlines()
        self.assertEqual(len(lines), 2)
        entry = json.loads(lines[0])
        self.assertEqual(entry["session_id"], SESSION)
        self.assertEqual(entry["task_id"], "UNITY-20260927-047")
        self.assertTrue(entry["command"].endswith(P + " list"))
        self.assertEqual(len(entry["marker_sha256"]), 64)

    def test_legacy_floor_does_not_match_the_rehearsal_form(self):
        # The pre-058 rule denies only args[0] == publish; the rehearsal form
        # starts with -config=, so the floor leaves it to the allowance.
        self.assertIsNone(self.hook._group_rules(self.hook._legacy_groups(self.command())))

    def test_config_with_every_allowed_path_inside(self):
        r = str(self.root)
        self.write_config({"rootDir": r + "/r", "FileSystemPublishEndpoints": {"x": {"rootDir": r + "/pub",
                           "linkMethod": "hardlink"}}, "databaseBackend": {"type": "leveldb", "dbPath": r + "/db"},
                           "packagePoolStorage": {"type": "local", "path": r + "/pool"},
                           "downloadConcurrency": 4, "gpgDisableSign": False})
        self.assertAllowed(self.command())

    # --- authorization marker ------------------------------------------------

    def test_marker_required(self):
        os.unlink(self.hook.REHEARSAL_MARKER)
        self.assertIn("authorization", self.assertDenied(self.command()))

    def test_marker_conditions(self):
        cases = {
            "expired": dict(not_before=stamp(timedelta(hours=-3)), not_after=stamp(timedelta(hours=-1))),
            "future": dict(not_before=stamp(timedelta(hours=1)), not_after=stamp(timedelta(hours=2))),
            "window": dict(not_before=stamp(timedelta(hours=-1)), not_after=stamp(timedelta(hours=24))),
            "reversed": dict(not_before=stamp(timedelta(hours=1)), not_after=stamp(timedelta(hours=-1))),
            "offset": dict(not_after=stamp(timedelta(hours=1)).replace("Z", "+00:00")),
            "not May": dict(authorized_by="C"),
            "not C": dict(recorded_by="B"),
            "root": dict(root="/var/tmp/other"),
            "session": dict(session_id="another-session"),
            "schema": dict(schema=2),
            "schema bool": dict(schema=True),
            "extra": dict(extra="x"),
            "missing reference": dict(reference=None),
            "empty reference": dict(reference=""),
        }
        for name, changes in cases.items():
            with self.subTest(name):
                self.write_marker(**changes)
                self.assertDenied(self.command())

    def test_marker_session_absent(self):
        self.assertDenied(self.command(), session=None)

    def test_marker_file_properties(self):
        marker = Path(self.hook.REHEARSAL_MARKER)
        os.chmod(marker, 0o620)
        self.assertDenied(self.command())
        os.chmod(marker, 0o600)
        real = self.coord / "real.json"
        marker.rename(real)
        marker.symlink_to(real)
        self.assertDenied(self.command())

    def test_coordinator_directory_properties(self):
        os.chmod(self.coord, 0o770)
        self.assertDenied(self.command())

    # --- command shape -------------------------------------------------------

    def test_command_shape(self):
        c = str(self.config)
        cases = [
            f"aptly -config={c} {P} list",                      # not the absolute binary
            f"{APTLY} -config {c} {P} list",                    # value as a separate token
            f"{APTLY} -config={c} -config={c} {P} list",        # two configs
            f"{APTLY} --config={c} -config={c} {P} list",
            f"{APTLY} {P} -config={c} list",                     # config after publish
            f"{APTLY} -config={c} {P} list ../x",                # ..
            f"{APTLY} -config={c} {P} repo -distribution=../../x u",
            f"{APTLY} -config={c} {P} list; true",               # separator
            f"{APTLY} -config={c} {P} list > /tmp/x",            # redirection
            f"{APTLY} -config={c} {P} list | cat",               # pipe
            f"{APTLY} -config={c} {P} list  ",                   # extra spaces
            f"{APTLY} -config={c} {P} 'list'",                   # quoting
            f"{APTLY} -config={c} {P} $X",                       # expansion
            f"{APTLY} -config={c} {P} task",                     # task
            f"{APTLY} -config={c} {P} api",                      # api
            f"{APTLY} -config={c} {P} {P} list",                 # publish twice
            f"HOME=/tmp {APTLY} -config={c} {P} list",           # assignment
            f"env {APTLY} -config={c} {P} list",                 # prefix
            f"sudo {APTLY} -config={c} {P} list",
            f"{APTLY} -config=relative/aptly.conf {P} list",     # relative config
            f"{APTLY} -config=/var/tmp/other/aptly.conf {P} list",
            f"{APTLY} -config={self.root}//aptly.conf {P} list",  # not normalised
            f"{APTLY} -config={c} {P} list\n{APTLY} -config={c} {P} drop x",
            f"{APTLY} -architectures {P} -config={c} repo list",   # a flag value as the command word
            f"{APTLY} -config={c} -architectures {P} repo list",
            f"{APTLY} -batch -config={c} {P} list",                # config not first
            f"{APTLY} -config={c} -batch {P} list",                # publish not second
            f"{APTLY} foo -config={c} {P} list",
        ]
        for command in cases:
            with self.subTest(command=command):
                self.assertDenied(command)

    # --- config content ------------------------------------------------------

    def test_config_content(self):
        r = str(self.root)
        cases = {
            "no rootDir": {"architectures": ["amd64"]},
            "rootDir live": {"rootDir": "/srv/aptly"},
            "rootDir outside": {"rootDir": "/var/tmp/elsewhere"},
            "rootDir tilde": {"rootDir": "~/.aptly"},
            "rootDir relative": {"rootDir": "r"},
            "rootDir dotdot": {"rootDir": r + "/../elsewhere"},
            "rootDir number": {"rootDir": 5},
            "rootDir empty": {"rootDir": ""},
            "dbPath live": {"rootDir": r + "/r", "databaseBackend": {"dbPath": "/srv/aptly/db"}},
            "db etcd": {"rootDir": r + "/r", "databaseBackend": {"type": "etcd"}},
            "db url": {"rootDir": r + "/r", "databaseBackend": {"type": "leveldb", "url": "http://x"}},
            "db url key": {"rootDir": r + "/r", "databaseBackend": {"url": "x"}},
            "db LevelDB": {"rootDir": r + "/r", "databaseBackend": {"type": "LevelDB"}},
            "pool outside": {"rootDir": r + "/r", "packagePoolStorage": {"path": "/srv/aptly/pool"}},
            "pool azure": {"rootDir": r + "/r", "packagePoolStorage": {"type": "azure"}},
            "endpoint live": {"rootDir": r + "/r", "FileSystemPublishEndpoints": {"x": {"rootDir": "/srv/aptly/public"}}},
            "endpoint link": {"rootDir": r + "/r", "FileSystemPublishEndpoints": {"x": {"rootDir": r + "/p", "linkMethod": "reflink"}}},
            "s3": {"rootDir": r + "/r", "S3PublishEndpoints": {}},
            "swift": {"rootDir": r + "/r", "SwiftPublishEndpoints": {"x": {}}},
            "azure": {"rootDir": r + "/r", "AzurePublishEndpoints": {}},
            "case variant": {"RootDir": r + "/r"},
            "unknown key": {"rootDir": r + "/r", "serveInAPIMode": True},
            "int as bool": {"rootDir": r + "/r", "downloadConcurrency": True},
            "int range": {"rootDir": r + "/r", "downloadConcurrency": 5000},
            "bool as int": {"rootDir": r + "/r", "gpgDisableSign": 1},
            "not an object": [{"rootDir": r + "/r"}],
        }
        for name, value in cases.items():
            with self.subTest(name):
                self.write_config(value)
                self.assertDenied(self.command())

    def test_config_encoding(self):
        r = str(self.root)
        cases = {
            "duplicate": '{"rootDir": "%s/r", "rootDir": "/srv/aptly"}' % r,
            "null": '{"rootDir": "%s/r", "logLevel": null}' % r,
            "nan": '{"rootDir": "%s/r", "downloadConcurrency": NaN}' % r,
            "float": '{"rootDir": "%s/r", "downloadConcurrency": 1.0}' % r,
            "comment": '{"rootDir": "%s/r" /* x */}' % r,
            "line comment": '{"rootDir": "%s/r"}\n// x' % r,
            "non-ascii": '{"rootDir": "%s/r", "logLevel": "é"}' % r,
            "escaped non-ascii": '{"rootDir": "%s/r", "logLevel": "\\u00e9"}' % r,
            "lone surrogate": '{"rootDir": "%s/r", "logLevel": "\\ud800"}' % r,
            "two values": '{"rootDir": "%s/r"} {}' % r,
            "yaml": "root_dir: %s/r\n" % r,
            "bom": "﻿" + '{"rootDir": "%s/r"}' % r,
        }
        for name, raw in cases.items():
            with self.subTest(name):
                self.write_config(None, raw=raw)
                self.assertDenied(self.command())

    def test_config_file_properties(self):
        os.chmod(self.config, 0o620)
        self.assertDenied(self.command())
        os.chmod(self.config, 0o600)
        real = self.root / "real.conf"
        self.config.rename(real)
        self.config.symlink_to(real)
        self.assertDenied(self.command())

    # --- root and tree -------------------------------------------------------

    def test_root_properties(self):
        os.chmod(self.root, 0o770)
        self.assertDenied(self.command())

    def test_root_symlink(self):
        base = Path(self.tmp.name)
        real = base / "real-root"
        self.root.rename(real)
        self.root.symlink_to(real)
        self.assertDenied(self.command())

    def outside(self):
        path = Path(self.tmp.name) / "outside"
        if not path.exists():
            path.mkdir(mode=0o700)
            (path / "file").write_text("x")
        return path

    def test_tree(self):
        cases = {}

        def link_out():
            (self.root / "db").symlink_to(self.outside())
        cases["directory link out"] = link_out

        def file_link_out():
            (self.root / "Release").symlink_to(self.outside() / "file")
        cases["file link out"] = file_link_out

        def hard_link_out():
            os.link(self.outside() / "file", self.root / "LOCK")
        cases["hard link out"] = hard_link_out

        def fifo():
            os.mkfifo(self.root / "fifo")
        cases["fifo"] = fifo

        def loose_dir():
            (self.root / "pool").mkdir(mode=0o700)
            os.chmod(self.root / "pool", 0o777)
        cases["group-writable directory"] = loose_dir

        def unlistable():
            (self.root / "db2").mkdir(mode=0o700)
            os.chmod(self.root / "db2", 0o300)
        cases["unlistable directory"] = unlistable

        for name, make in cases.items():
            with self.subTest(name):
                self.tearDown()
                self.setUp()
                make()
                self.assertDenied(self.command())

    def test_tree_links_inside_are_fine(self):
        (self.root / "pool").mkdir(mode=0o700)
        (self.root / "pool" / "a.deb").write_text("x")
        os.link(self.root / "pool" / "a.deb", self.root / "b.deb")
        (self.root / "by-hash").symlink_to(self.root / "pool")
        self.assertAllowed(self.command())

    def test_too_many_entries(self):
        self.hook.REHEARSAL_MAX_ENTRIES = 3
        for i in range(5):
            (self.root / f"f{i}").write_text("x")
        self.assertDenied(self.command())

    def test_config_too_large(self):
        self.write_config(None, raw='{"rootDir": "%s/r", "logLevel": "%s"}' % (self.root, "x" * 70000))
        self.assertIn("too large", self.assertDenied(self.command()))

    def test_coordinator_directory_symlink(self):
        base = Path(self.tmp.name)
        self.coord.rename(base / "real-coordinator")
        self.coord.symlink_to(base / "real-coordinator")
        self.assertDenied(self.command())

    def test_mount_under_root(self):
        fake = Path(self.tmp.name) / "mountinfo"
        fake.write_text("36 35 98:0 / %s rw - ext4 /dev/x rw\n" % str(self.root / "db").replace(" ", "\\040"))
        self.hook.MOUNTINFO = str(fake)
        self.assertIn("mount point", self.assertDenied(self.command()))

    def test_binary_must_be_roots_aptly(self):
        fake = Path(self.tmp.name) / "aptly"
        fake.write_text("#!/bin/sh\n")
        os.chmod(fake, 0o755)
        self.hook.APTLY_BINARY = str(fake)
        command = self.command().replace(APTLY, str(fake), 1)
        self.assertIn("root-owned", self.assertDenied(command))

    # --- audit log -----------------------------------------------------------

    def test_log_must_be_appendable(self):
        log = Path(self.hook.REHEARSAL_LOG)
        log.symlink_to(Path(self.tmp.name) / "elsewhere.log")
        self.assertDenied(self.command())

    def test_log_permissions(self):
        log = Path(self.hook.REHEARSAL_LOG)
        log.write_text("")
        os.chmod(log, 0o666)
        self.assertDenied(self.command())


class RehearsalWithoutAuthorizationTest(unittest.TestCase):
    """Through the real hook process and its real paths: without C's marker the
    rehearsal command stays denied, as under 058."""

    def test_denied_without_marker(self):
        if os.path.exists("/home/claude/coordinator/rehearsal-authorization.json"):
            self.skipTest("a rehearsal authorization is active on this machine")
        command = " ".join([APTLY, "-config=/var/tmp/aptly-rehearsal/aptly.conf", P, "list"])
        payload = json.dumps({"tool_name": "Bash", "session_id": SESSION,
                              "tool_input": {"command": command}})
        result = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)


if __name__ == "__main__":
    unittest.main()
