#!/usr/bin/env python3
"""UNITY-20261008-004: scripts/backup_aptly_db.py copies a repository db/ under
a shared flock on db/LOCK, writes db.sha256 and backup.json, exits 0 only for
a complete copy equal to the live db, 1 for a bad copy, 2 for a refusal.

Every case runs the script for real against a scratch live root (--live),
never /srv. PATH starts with a directory of fake tools: pidof (no repository
tool running unless a case says so) and, where a case needs it, cp.
Run: python3 -m unittest discover -s scripts/tests
"""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "backup_aptly_db.py"
REAL_CP = "/bin/cp"


class BackupDbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.live = self.t / "live"
        db = self.live / "db"
        db.mkdir(parents=True)
        (db / "LOCK").write_bytes(b"")
        (db / "LOG").write_bytes(b"")
        (db / "000001.log").write_bytes(b"")
        (db / "CURRENT").write_text("MANIFEST-000002\n")
        (db / "MANIFEST-000002").write_bytes(b"\x00manifest")
        (db / "000005.ldb").write_bytes(os.urandom(4096))
        self.bin = self.t / "bin"
        self.bin.mkdir()
        self.fake("pidof", "exit 1")  # nothing running
        self.home = self.t / "home"
        self.home.mkdir()
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}", HOME=str(self.home),
                        PYTHONDONTWRITEBYTECODE="1")

    def tearDown(self):
        self.tmp.cleanup()

    def fake(self, name, body):
        path = self.bin / name
        path.write_text(f"#!/bin/sh\n{body}\n")
        path.chmod(0o755)

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--live", str(self.live), *args],
                              capture_output=True, text=True, env=self.env, timeout=60)

    def dst(self, name="bk"):
        return self.t / "backups" / name

    def assert_refused(self, result, fragment, dst=None):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(fragment, result.stderr)
        if dst is not None:
            self.assertFalse(dst.exists(), "a refusal must not create the backup directory")

    def test_good_copy(self):
        dst = self.dst()
        result = self.run_script(str(dst), "--task", "UNITY-20990101-001")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(dst), result.stdout)
        self.assertEqual(dst.stat().st_mode & 0o777, 0o700)
        lines = (dst / "db.sha256").read_text().splitlines()
        names = [line.split("  ", 1)[1] for line in lines]
        self.assertEqual(names, sorted(f"db/{p.name}" for p in (self.live / "db").iterdir()))
        self.assertIn("db/LOCK", names)  # empty files are listed
        self.assertIn("db/000001.log", names)
        for line in lines:
            digest, name = line.split("  ", 1)
            self.assertEqual(digest, hashlib.sha256((self.live / name).read_bytes()).hexdigest())
        record = json.loads((dst / "backup.json").read_text())
        self.assertEqual((record["complete"], record["equal_to_live"], record["files"], record["task"]),
                         (True, True, 6, "UNITY-20990101-001"))
        self.assertEqual(record["live"], str(self.live.resolve()))
        self.assertEqual(record["list_sha256"], hashlib.sha256((dst / "db.sha256").read_bytes()).hexdigest())
        self.assertEqual((dst / "db" / "000005.ldb").read_bytes(), (self.live / "db" / "000005.ldb").read_bytes())

    def test_default_directory_named_after_the_task(self):
        result = self.run_script("--task", "UNITY-20990101-001")
        self.assertEqual(result.returncode, 0, result.stderr)
        made = list((self.home / "backups").iterdir())
        self.assertEqual(len(made), 1)
        self.assertRegex(made[0].name, r"^UNITY-20990101-001-\d{8}T\d{6}Z$")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(p.name.startswith("aptly-db-") for p in (self.home / "backups").iterdir()))

    def test_lock_held_by_another_process_refused(self):
        holder = subprocess.Popen([sys.executable, "-c",
                                   "import fcntl,sys,time; f=open(sys.argv[1],'rb'); fcntl.flock(f, fcntl.LOCK_EX); "
                                   "print('held', flush=True); time.sleep(30)", str(self.live / "db" / "LOCK")],
                                  stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "held")
            dst = self.dst()
            self.assert_refused(self.run_script(str(dst)), "is locked", dst)
        finally:
            holder.kill()
            holder.wait()
        self.assertEqual(self.run_script(str(self.dst("after"))).returncode, 0)

    def test_shared_lock_held_while_copying(self):
        """A fake cp checks that an exclusive lock is impossible during the copy."""
        probe = self.t / "probe.txt"
        self.fake("cp", f"""{sys.executable} -c 'import fcntl,sys
f=open(sys.argv[1],"rb")
try:
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB); print("free")
except BlockingIOError:
    print("held")' "{self.live}/db/LOCK" > "{probe}"
exec {REAL_CP} "$@\"""")
        result = self.run_script(str(self.dst()))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(probe.read_text().strip(), "held")

    def test_lock_held_through_the_second_read(self):
        """A writer waiting for the exclusive lock changes the db the moment it gets it.
        The backup must still hold its shared lock while it reads the live db again, so
        the writer's change lands after the comparison: exit 0, copy equal. A large
        file read early keeps the second read long enough for a released lock to show."""
        (self.live / "db" / "000002.ldb").write_bytes(os.urandom(48 * 1024 * 1024))
        flag = self.t / "copied"
        done = self.t / "writer-done"
        writer = subprocess.Popen([sys.executable, "-c", f"""import fcntl, os, time
while not os.path.exists({str(flag)!r}):
    time.sleep(0.01)
f = open({str(self.live / 'db' / 'LOCK')!r}, 'rb')
fcntl.flock(f, fcntl.LOCK_EX)
open({str(self.live / 'db' / 'MANIFEST-000002')!r}, 'ab').write(b'written')
open({str(done)!r}, 'w').close()
"""])
        try:
            self.fake("cp", f'{REAL_CP} "$@" && touch "{flag}"')
            dst = self.dst()
            result = self.run_script(str(dst))
            writer.wait(timeout=30)
        finally:
            writer.kill()
        self.assertTrue(done.exists())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads((dst / "backup.json").read_text())["equal_to_live"])
        self.assertNotEqual((dst / "db" / "MANIFEST-000002").read_bytes(),
                            (self.live / "db" / "MANIFEST-000002").read_bytes())

    def test_running_tool_refused(self):
        self.fake("pidof", "echo 4242; exit 0")
        dst = self.dst()
        self.assert_refused(self.run_script(str(dst)), "process is running", dst)

    def test_missing_pidof_refused(self):
        (self.bin / "pidof").unlink()
        self.env["PATH"] = str(self.bin)  # no system pidof either; the script runs through sys.executable
        dst = self.dst()
        self.assert_refused(self.run_script(str(dst)), "pidof is not available", dst)

    def test_existing_backup_dir_refused(self):
        dst = self.dst()
        dst.mkdir(parents=True)
        self.assert_refused(self.run_script(str(dst)), "exists")
        link = self.dst("link")
        link.symlink_to(self.t / "nowhere")
        self.assert_refused(self.run_script(str(link)), "exists")

    def test_backup_dir_inside_live_refused(self):
        self.assert_refused(self.run_script(str(self.live / "copy")), "inside the live", self.live / "copy")
        alias = self.t / "alias"
        alias.symlink_to(self.live)
        self.assert_refused(self.run_script(str(alias / "copy")), "inside the live", self.live / "copy")

    def test_symlinked_live_root(self):
        alias = self.t / "live-alias"
        alias.symlink_to(self.live)
        result = subprocess.run([sys.executable, str(SCRIPT), "--live", str(alias), str(self.dst())],
                                capture_output=True, text=True, env=self.env, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.dst() / "backup.json").read_text())["live"], str(self.live.resolve()))

    def test_missing_db_or_lock_refused(self):
        (self.live / "db" / "LOCK").unlink()
        dst = self.dst()
        self.assert_refused(self.run_script(str(dst)), "no repository database", dst)
        self.live = self.t / "empty"
        self.live.mkdir()
        self.assert_refused(self.run_script(str(dst)), "no repository database", dst)

    def test_live_changed_during_copy(self):
        self.fake("cp", f'{REAL_CP} "$@" && echo changed >> "{self.live}/db/000005.ldb"')
        dst = self.dst()
        result = self.run_script(str(dst))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("differs from the live db", result.stderr)
        record = json.loads((dst / "backup.json").read_text())
        self.assertEqual((record["complete"], record["equal_to_live"]), (True, False))

    def test_copy_failed(self):
        self.fake("cp", 'echo "cp: disk full" >&2; exit 1')
        dst = self.dst()
        result = self.run_script(str(dst))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("the copy failed", result.stderr)
        record = json.loads((dst / "backup.json").read_text())
        self.assertEqual((record["complete"], record["equal_to_live"]), (False, False))
        self.assertIn("disk full", record["cp_error"])


if __name__ == "__main__":
    unittest.main()
