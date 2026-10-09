#!/usr/bin/env python3
"""The publisher's signer steps (permission model phase 5, UNITY-20260929-024):
repository state, the proposal publication from the live database into the
task's tree, the signer's answer, the switch environment, refresh and /live
after the switch, the record. aptly, the client and the signer are injected;
nothing here runs aptly or reaches a signer.
Run: python3 -m unittest discover -s scripts/tests
"""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
spec = importlib.util.spec_from_file_location("publish_aptly", HERE.parent / "publish_aptly.py")
publish_aptly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish_aptly)
import approval_record  # noqa: E402
import signer_client  # noqa: E402

TASK = "UNITY-20990101-001"
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


class Result:
    def __init__(self, rc=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = rc, stdout, stderr


class RecordingAptly:
    """A fake subprocess.run for aptly: records every call, answers per subcommand."""
    def __init__(self, fail_publish=False):
        self.calls, self.fail_publish = [], fail_publish

    def __call__(self, command, check=False, capture_output=False, text=False, env=None):
        self.calls.append((list(command), env))
        if command[0] == "aptly" and "snapshot" in command and self.fail_publish:
            return Result(1, stderr="boom")
        return Result(0)


class SignerStepsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.public = self.base / "public"
        self.dist = self.public / "dists" / "resolute"
        self.dist.mkdir(parents=True)
        (self.dist / "Release").write_text("Origin: . resolute\nSuite: resolute\nArchitectures: amd64\nComponents: main\n")
        self.live_config = self.base / "aptly.conf"
        self.live_config.write_text(json.dumps({"rootDir": "/srv/aptly", "architectures": ["amd64"],
                                                "FileSystemPublishEndpoints": {}}))
        self.proposal_root = self.base / "rehearsal"

    def tearDown(self):
        self.tmp.cleanup()

    def test_signer_mode_by_client_config_presence(self):
        self.assertFalse(publish_aptly.signer_mode(self.base / "client.json"))
        (self.base / "client.json").write_text("{}")
        self.assertTrue(publish_aptly.signer_mode(self.base / "client.json"))

    def test_repository_state(self):
        error, notes = publish_aptly.repository_state(self.public, "resolute", NOW)
        self.assertIsNone(error); self.assertEqual(notes, [])
        (self.dist / "InRelease").write_text("Origin: . resolute\nDate: Fri, 09 Oct 2026 10:00:00 UTC\n")  # aptly's: no Valid-Until
        self.assertIsNone(publish_aptly.repository_state(self.public, "resolute", NOW)[0])
        (self.dist / "InRelease").write_text("Valid-Until: Sat, 10 Oct 2026 10:00:00 UTC\n")
        self.assertIsNone(publish_aptly.repository_state(self.public, "resolute", NOW)[0])
        (self.dist / "InRelease").write_text("Valid-Until: Thu, 08 Oct 2026 10:00:00 UTC\n")
        error, _ = publish_aptly.repository_state(self.public, "resolute", NOW)
        self.assertIn("the repository has expired", error)
        (self.dist / "InRelease").write_text("Valid-Until: not a date\n")
        self.assertIn("unreadable", publish_aptly.repository_state(self.public, "resolute", NOW)[0])
        (self.dist / "InRelease").write_text("Valid-Until: Sat, 10 Oct 2026 10:00:00 UTC\n")
        (self.dist / "Release.tmp").write_text("x")
        (self.dist / "main" / "binary-amd64").mkdir(parents=True)
        (self.dist / "main" / "binary-amd64" / "Packages.tmp.gz").write_text("x")
        error, notes = publish_aptly.repository_state(self.public, "resolute", NOW)
        self.assertIsNone(error)
        self.assertEqual(len(notes), 1)
        self.assertIn("the last switch was refused", notes[0])
        self.assertIn("Release.tmp", notes[0])
        self.assertTrue((self.dist / "Release.tmp").exists())  # reported, never deleted

    def test_proposal_publication_commands_and_config(self):
        aptly = RecordingAptly()
        public, error = publish_aptly.publish_proposal(TASK, "snap-1", "resolute", ".", run=aptly,
                                                       live_config_path=self.live_config, public_dir=self.public,
                                                       proposal_root=self.proposal_root)
        self.assertIsNone(error)
        self.assertEqual(public, self.proposal_root / TASK / "public")
        config_path = self.proposal_root / TASK / "aptly.conf"
        written = json.loads(config_path.read_text())
        live = json.loads(self.live_config.read_text())
        self.assertEqual({k: v for k, v in written.items() if k != "FileSystemPublishEndpoints"},
                         {k: v for k, v in live.items() if k != "FileSystemPublishEndpoints"})
        self.assertEqual(written["FileSystemPublishEndpoints"],
                         {f"proposal-{TASK}": {"rootDir": str(public), "linkMethod": "copy"}})
        self.assertEqual(len(aptly.calls), 1)
        self.assertEqual(aptly.calls[0][0], ["aptly", f"-config={config_path}", "publish", "snapshot", "-skip-signing",
                                             "-skip-contents", "-architectures=amd64", "-distribution=resolute",
                                             "-component=main", "snap-1", f"filesystem:proposal-{TASK}:."])
        self.assertFalse(os.stat(self.proposal_root / TASK).st_mode & 0o022)
        # a rerun drops the earlier publication of this task first, then republishes
        public.mkdir(parents=True, exist_ok=True)
        aptly = RecordingAptly()
        publish_aptly.publish_proposal(TASK, "snap-1", "resolute", ".", run=aptly, live_config_path=self.live_config,
                                       public_dir=self.public, proposal_root=self.proposal_root)
        self.assertEqual([c[0][2:4] for c in aptly.calls], [["publish", "drop"], ["publish", "snapshot"]])
        self.assertEqual(aptly.calls[0][0][4:], ["resolute", f"filesystem:proposal-{TASK}:."])
        # a failed publication is an error with aptly's text; drop removes the tree
        aptly = RecordingAptly(fail_publish=True)
        public, error = publish_aptly.publish_proposal(TASK, "snap-1", "resolute", ".", run=aptly,
                                                       live_config_path=self.live_config, public_dir=self.public,
                                                       proposal_root=self.proposal_root)
        self.assertIsNone(public)
        self.assertIn("boom", error)
        publish_aptly.drop_proposal(TASK, "resolute", ".", run=aptly, proposal_root=self.proposal_root)
        self.assertFalse((self.proposal_root / TASK).exists())
        self.assertEqual(aptly.calls[-1][0][2:4], ["publish", "drop"])
        # the architectures come from the live Release, not the config
        (self.dist / "Release").write_text("Architectures: amd64 i386\n")
        aptly = RecordingAptly()
        publish_aptly.publish_proposal(TASK, "snap-1", "resolute", ".", run=aptly, live_config_path=self.live_config,
                                       public_dir=self.public, proposal_root=self.proposal_root)
        self.assertIn("-architectures=amd64,i386", aptly.calls[-1][0])

    def test_switch_environment_has_the_standin_first(self):
        root = self.base / "repo"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "gpg_standin.py").write_text("#!/bin/sh\n")
        env = publish_aptly.signer_env(root, TASK, proposal_root=self.proposal_root)
        bindir = self.proposal_root / TASK / "bin"
        self.assertTrue(env["PATH"].startswith(str(bindir) + ":"))
        self.assertEqual(os.readlink(bindir / "gpg"), str(root / "scripts" / "gpg_standin.py"))
        publish_aptly.signer_env(root, TASK, proposal_root=self.proposal_root)  # idempotent
        # consume_and_switch passes the environment to aptly (the approval consumption is faked)
        from unittest import mock
        aptly = RecordingAptly()
        show = lambda args: Result(0, stdout="Sources:\n  main: snap-1 [snapshot]\n")
        with mock.patch.object(publish_aptly.approval_record, "consume", return_value=(self.base / "used.json", "s" * 64)), \
                mock.patch.object(publish_aptly.approval_record, "set_outcome", return_value="t" * 64):
            used_path, used_sha, error = publish_aptly.consume_and_switch(
                TASK, ({}, "s" * 64, b"{}"), ["aptly", "publish", "switch", "-skip-contents", "resolute", "snap-1"],
                ["publish", "show", "resolute"], "snap-1", "demo", "1.0", run=aptly, show=show, log=lambda *a: None, env=env)
        self.assertIsNone(error)
        self.assertEqual(len(aptly.calls), 1)
        self.assertEqual(aptly.calls[0][1]["PATH"], env["PATH"])
        self.assertIn("-skip-contents", aptly.calls[0][0])

    def test_after_switch_runs_live_even_when_refresh_fails(self):
        client = {"url": "http://127.0.0.1:9"}
        calls = []

        def refresh_ok(c, task, switch):
            calls.append(("refresh", task, switch)); return 0

        def refresh_bad(c, task, switch):
            calls.append(("refresh", task, switch)); raise signer_client.core.Refused("R2: served index differs")

        def live_ok():
            calls.append(("live",)); return "setid"

        def live_bad():
            calls.append(("live",)); raise signer_client.core.Refused("not the signer's InRelease")

        self.assertEqual(publish_aptly.after_switch(client, TASK, refresh=refresh_ok, live=live_ok),
                         {"refresh": "OK", "live": "OK setid"})
        outcome = publish_aptly.after_switch(client, TASK, refresh=refresh_bad, live=live_ok)
        self.assertEqual(outcome["refresh"], "FAILED: R2: served index differs")
        self.assertEqual(outcome["live"], "OK setid")
        self.assertEqual([c[0] for c in calls], ["refresh", "live", "refresh", "live"])
        outcome = publish_aptly.after_switch(client, TASK, refresh=refresh_ok, live=live_bad)
        self.assertEqual(outcome["live"], "FAILED: not the signer's InRelease")

    def test_client_config_validation(self):
        path = self.base / "client.json"
        path.write_text(json.dumps({"url": "http://x", "public_root": "/p"}))
        with self.assertRaises(signer_client.core.Refused) as caught:
            signer_client.load_config(path)
        self.assertIn("missing keyring, store, marker_dir, log", str(caught.exception))
        path.write_text(json.dumps({"url": "http://x", "public_root": "~/p", "keyring": "k", "store": "~/s",
                                    "marker_dir": "m", "log": "l"}))
        config = signer_client.load_config(path)
        self.assertEqual((config["distribution"], config["timeout"]), ("resolute", 120))
        self.assertFalse(config["store"].startswith("~"))
        path.write_text("{not json")
        with self.assertRaises(signer_client.core.Refused):
            signer_client.load_config(path)

    def test_cadence_task_name(self):
        self.assertTrue(signer_client.TASK_RE.fullmatch("cadence"))
        self.assertTrue(signer_client.TASK_RE.fullmatch("UNITY-20261009-001"))
        self.assertIsNone(signer_client.TASK_RE.fullmatch("UNITY-2026-1"))

    def test_publication_tools_include_the_signer_side(self):
        for tool in ("scripts/signer_client.py", "scripts/gpg_standin.py", "signer/signer_core.py"):
            self.assertIn(tool, approval_record.PUBLICATION_TOOLS)
            self.assertTrue((HERE.parent.parent / tool).is_file())


class SignerPrepareTest(unittest.TestCase):
    """The orchestration before the switch (signer_prepare), its collaborators
    injected: legacy mode; an expired repository; a failed proposal
    publication; the signer's refusal; pending exits 3 after dropping the
    proposal tree and before anything of C's approval; approved gives the
    stand-in environment and the record's signer block."""

    def setUp(self):
        from unittest import mock
        self.mock = mock
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "repo" / "scripts").mkdir(parents=True)
        (self.base / "repo" / "scripts" / "gpg_standin.py").write_text("#!/bin/sh\n")
        self.calls = []
        self.out = __import__("io").StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def prepare(self, answer=None, mode=True, state=(None, []), publish=(Path("/x/public"), None), config=None):
        mock, mod = self.mock, publish_aptly
        patches = [mock.patch.object(mod, "signer_mode", return_value=mode),
                   mock.patch.object(mod, "repository_state", return_value=state),
                   mock.patch.object(mod, "publish_proposal", return_value=publish),
                   mock.patch.object(mod, "drop_proposal", side_effect=lambda *a, **k: self.calls.append("drop")),
                   mock.patch.object(mod, "PROPOSAL_ROOT", self.base / "rehearsal"),
                   mock.patch.object(mod.signer_client, "load_config",
                                     side_effect=config or (lambda path=None: {"url": "u"}))]
        if isinstance(answer, Exception):
            patches.append(mock.patch.object(mod.signer_client, "propose_answer", side_effect=answer))
        else:
            patches.append(mock.patch.object(mod.signer_client, "propose_answer",
                                             side_effect=lambda c, p, t: self.calls.append(("propose", str(p), t)) or answer))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return mod.signer_prepare(self.base / "repo", TASK, "snap-1", "resolute", ".", out=self.out)

    def test_legacy_mode(self):
        info, env, client, rc = self.prepare(mode=False)
        self.assertEqual((info, env, client, rc), ({"mode": "legacy"}, None, None, None))
        self.assertEqual(self.calls, [])

    def test_expired_repository_stops_before_the_proposal(self):
        info, env, client, rc = self.prepare(state=("the repository has expired (Valid-Until passed)", []))
        self.assertEqual(rc, 2)
        self.assertEqual(self.calls, [])

    def test_client_config_problem_stops(self):
        def bad(path=None):
            raise signer_client.core.Refused("client configuration: missing keyring")
        info, env, client, rc = self.prepare(config=bad)
        self.assertEqual(rc, 2)
        self.assertEqual(self.calls, [])

    def test_failed_proposal_publication(self):
        info, env, client, rc = self.prepare(publish=(None, "proposal publication failed (aptly rc 1): boom"))
        self.assertEqual(rc, 2)
        self.assertEqual(self.calls, ["drop"])

    def test_signer_refusal(self):
        info, env, client, rc = self.prepare(answer=signer_client.core.Refused("the signer refused: the proposal lacks the .deb"))
        self.assertEqual(rc, 2)
        self.assertEqual(self.calls, ["drop"])

    def test_pending_exits_3_after_dropping_and_touches_no_approval(self):
        info, env, client, rc = self.prepare(answer={"proposal": "p1", "status": "pending", "approved_by": None,
                                                   "reasons": ["source x is not in last-live: a new package is never routine"]})
        self.assertEqual(rc, publish_aptly.PENDING_EXIT)
        self.assertEqual(rc, 3)
        self.assertEqual(self.calls, [("propose", "/x/public", TASK), "drop"])
        self.assertIn("waiting for May on the signer console (proposal p1)", self.out.getvalue())
        self.assertIn("never routine", self.out.getvalue())
        self.assertIsNone(info)

    def test_approved_gives_the_standin_environment(self):
        info, env, client, rc = self.prepare(answer={"proposal": "p1", "status": "approved", "approved_by": "policy", "reasons": []})
        self.assertIsNone(rc)
        self.assertEqual(info, {"mode": "signer", "proposal": "p1", "approved_by": "policy"})
        self.assertEqual(client, {"url": "u"})
        bindir = self.base / "rehearsal" / TASK / "bin"
        self.assertTrue(env["PATH"].startswith(str(bindir) + ":"))
        self.assertEqual(os.readlink(bindir / "gpg"), str(self.base / "repo" / "scripts" / "gpg_standin.py"))
        self.assertEqual(self.calls, [("propose", "/x/public", TASK)])  # the tree stays for the switch


if __name__ == "__main__":
    unittest.main()
