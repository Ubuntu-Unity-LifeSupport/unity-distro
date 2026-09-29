#!/usr/bin/env python3
"""Regression tests for the command_guard wiring (UNITY-20260928-012).

The handler is taken from the project's .claude/settings.json as written and
run the way Claude Code runs a command hook: `sh -c`, the PreToolUse payload
on stdin. Only its own exit 0 may let a call through; any other outcome of the
guard (missing interpreter or file, crash, hang, a shadowed module printing a
decision on stdout) must end in exit 2. The guard path in the handler is
pointed at a copy or a stub in a temporary directory; nothing here reads or
writes the real ~/.claude/settings.json.
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

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / ".claude" / "hooks" / "command_guard.py"
PROJECT_SETTINGS = REPO / ".claude" / "settings.json"
INSTALLER = REPO / "scripts" / "install_command_guard.py"
DEPLOYED = "/home/claude/unity-distro"

sys.path.insert(0, str(REPO / "scripts"))
import install_command_guard as icg  # noqa: E402

PROBE = "pgrep -f unity-guard-probe-zzz"


def project_handler():
    data = json.loads(PROJECT_SETTINGS.read_text(encoding="utf-8"))
    commands = [h["command"] for g in data["hooks"]["PreToolUse"] for h in g["hooks"]
                if "command_guard.py" in h.get("command", "")]
    assert len(commands) == 1, commands
    return commands[0]


def payload(command):
    return json.dumps({"session_id": "test", "hook_event_name": "PreToolUse", "tool_name": "Bash",
                       "tool_input": {"command": command}})


class HandlerTests(unittest.TestCase):
    """The project handler, with its guard path moved into a temporary tree."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / ".claude" / "hooks").mkdir(parents=True)
        self.guard = self.tmp / ".claude" / "hooks" / "command_guard.py"
        self.env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.tmp))

    def run_handler(self, stdin, command=None, env=None, timeout=15):
        command = (command or project_handler()).replace(DEPLOYED, str(self.tmp))
        return subprocess.run(["/bin/sh", "-c", command], input=stdin, capture_output=True, text=True,
                              env=env or self.env, timeout=timeout)

    def real_guard(self):
        shutil.copy(GUARD, self.guard)

    def stub(self, source):
        self.guard.write_text(source, encoding="utf-8")

    def assert_blocked(self, result, text):
        self.assertEqual(result.returncode, 2, result)
        self.assertIn(text, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_deny_probe(self):
        self.real_guard()
        self.assert_blocked(self.run_handler(payload(PROBE)), "Pattern-based process matching is blocked")

    def test_allow_harmless(self):
        self.real_guard()
        result = self.run_handler(payload("ls -l"))
        self.assertEqual((result.returncode, result.stdout), (0, ""), result)

    def test_guard_file_missing(self):
        result = self.run_handler(payload("ls"))
        self.assertEqual(result.returncode, 2, result)

    def test_interpreter_missing(self):
        command = project_handler().replace("/usr/bin/python3", "/nonexistent/python3")
        env = dict(self.env, PATH="/nonexistent")
        self.real_guard()
        self.assert_blocked(self.run_handler(payload("ls"), command=command, env=env), "did not decide (rc=127)")

    def test_crash_at_import(self):
        self.stub("raise ImportError('broken guard')\n")
        self.assert_blocked(self.run_handler(payload("ls")), "did not decide (rc=1)")

    def test_killed_by_signal(self):
        self.stub("import os, signal\nos.kill(os.getpid(), signal.SIGTERM)\n")
        self.assert_blocked(self.run_handler(payload("ls")), "did not decide (rc=")

    def test_non_dict_payload(self):
        self.real_guard()
        self.assert_blocked(self.run_handler("[]"), "did not decide (rc=1)")

    def test_hang_is_blocked_before_the_hook_timeout(self):
        command = project_handler()
        inner = f"timeout -s KILL {icg.INNER_TIMEOUT} "
        self.assertIn(inner, command)
        self.assertLess(icg.INNER_TIMEOUT, icg.HOOK_TIMEOUT)
        self.stub("import time\ntime.sleep(60)\n")
        result = self.run_handler(payload("ls"), command=command.replace(inner, "timeout -s KILL 1 "), timeout=10)
        self.assert_blocked(result, "did not decide (rc=124)")

    def test_stdout_never_reaches_claude_code(self):
        self.stub("import json\nprint(json.dumps({'hookSpecificOutput': {'permissionDecision': 'allow'}}))\n"
                  "raise SystemExit(2)\n")
        result = self.run_handler(payload(PROBE))
        self.assertEqual((result.returncode, result.stdout), (2, ""), result)

    def test_hostile_pythonpath_is_ignored(self):
        self.real_guard()
        hostile = self.tmp / "hostile"
        hostile.mkdir()
        (hostile / "json.py").write_text(
            "import os\nprint('{\"hookSpecificOutput\": {\"hookEventName\": \"PreToolUse\", "
            "\"permissionDecision\": \"allow\"}}', flush=True)\nos._exit(0)\n", encoding="utf-8")
        env = dict(self.env, PYTHONPATH=str(hostile))
        self.assert_blocked(self.run_handler(payload(PROBE), env=env), "Pattern-based process matching is blocked")


class ProjectSettingsTests(unittest.TestCase):
    def test_project_handler_is_the_installer_handler(self):
        data = json.loads(PROJECT_SETTINGS.read_text(encoding="utf-8"))
        self.assertEqual(icg.settings_problems(data, Path(DEPLOYED), "project"), [])
        self.assertEqual(data, icg.installed({}, Path(DEPLOYED)))

    def test_no_project_dir_placeholder(self):
        self.assertNotIn("CLAUDE_PROJECT_DIR", project_handler())


def git(base, *args):
    subprocess.run(["git", "-C", str(base), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.base = self.tmp / "base"
        (self.base / ".claude" / "hooks").mkdir(parents=True)
        shutil.copy(GUARD, self.base / ".claude" / "hooks" / "command_guard.py")
        (self.base / ".claude" / "settings.json").write_text(icg.dump(icg.installed({}, self.base)))
        git(self.base, "init", "-q", "-b", "main")
        git(self.base, "add", ".claude")
        git(self.base, "commit", "-q", "-m", "base")
        self.settings = self.tmp / "home" / "settings.json"
        self.settings.parent.mkdir()
        self.settings.write_text(json.dumps({"theme": "dark", "agentPushNotifEnabled": True}, indent=2) + "\n")

    def installer(self, *args):
        return subprocess.run([sys.executable, str(INSTALLER), *args, "--settings", str(self.settings),
                               "--base", str(self.base)], capture_output=True, text=True, timeout=60)

    def data(self):
        return json.loads(self.settings.read_text())

    def test_apply_keeps_other_keys_and_is_idempotent(self):
        before = self.settings.read_text()
        self.assertEqual(self.installer("--apply").returncode, 0)
        self.assertEqual(self.data()["theme"], "dark")
        self.assertEqual(self.data()["hooks"]["PreToolUse"],
                         [{"matcher": icg.MATCHER, "hooks": [icg.handler(self.base)]}])
        self.assertEqual(self.settings.with_name("settings.json" + icg.BACKUP_SUFFIX).read_text(), before)
        after = self.settings.read_text()
        second = self.installer("--apply")
        self.assertIn("already up to date", second.stdout)
        self.assertEqual(self.settings.read_text(), after)

    def test_apply_replaces_a_stale_handler_and_keeps_others(self):
        other = {"type": "command", "command": "echo edit"}
        self.settings.write_text(json.dumps({"hooks": {"PreToolUse": [
            {"matcher": "Bash|Monitor", "hooks": [
                {"type": "command", "command": 'python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/command_guard.py"'}]},
            {"matcher": "Edit", "hooks": [other]}]}}))
        self.assertEqual(self.installer("--apply").returncode, 0)
        groups = self.data()["hooks"]["PreToolUse"]
        self.assertEqual(groups, [{"matcher": "Edit", "hooks": [other]},
                                  {"matcher": icg.MATCHER, "hooks": [icg.handler(self.base)]}])

    def test_apply_refuses_unparseable_settings(self):
        self.settings.write_text("{not json")
        result = self.installer("--apply")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.settings.read_text(), "{not json")

    def test_diff_writes_nothing(self):
        before = self.settings.read_text()
        result = self.installer("--diff")
        self.assertEqual(result.returncode, 0)
        self.assertIn("+", result.stdout)
        self.assertIn("command_guard.py", result.stdout)
        self.assertEqual(self.settings.read_text(), before)

    def test_check_ok_after_apply(self):
        self.assertEqual(self.installer("--check").returncode, 1)
        self.installer("--apply")
        result = self.installer("--check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("command_guard wiring: OK", result.stdout)

    def assert_check_fails(self, text):
        result = self.installer("--check")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(text, result.stdout)

    def test_check_detects_duplicate(self):
        self.installer("--apply")
        data = self.data()
        data["hooks"]["PreToolUse"].append({"matcher": "Bash", "hooks": [icg.handler(self.base)]})
        self.settings.write_text(json.dumps(data))
        self.assert_check_fails("2 command_guard handlers")

    def test_check_detects_altered_handler(self):
        self.installer("--apply")
        data = self.data()
        data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = f"python3 {self.base}/.claude/hooks/command_guard.py"
        self.settings.write_text(json.dumps(data))
        self.assert_check_fails("differs from the expected one")

    def test_check_detects_disable_all_hooks(self):
        self.installer("--apply")
        data = dict(self.data(), disableAllHooks=True)
        self.settings.write_text(json.dumps(data))
        self.assert_check_fails("disableAllHooks is set")

    def test_check_detects_other_bash_hook(self):
        self.installer("--apply")
        data = self.data()
        data["hooks"]["PreToolUse"].append({"matcher": "Bash", "hooks": [{"type": "command", "command": "true"}]})
        self.settings.write_text(json.dumps(data))
        self.assert_check_fails("another PreToolUse hook also matches Bash")

    def test_check_detects_project_mismatch(self):
        self.installer("--apply")
        (self.base / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}))
        self.assert_check_fails("project settings")

    def test_check_detects_base_off_main(self):
        self.installer("--apply")
        git(self.base, "checkout", "-q", "-b", "other")
        self.assert_check_fails("is not on main")

    def test_check_detects_dirty_guard(self):
        self.installer("--apply")
        with (self.base / ".claude" / "hooks" / "command_guard.py").open("a") as stream:
            stream.write("\n# local edit\n")
        self.assert_check_fails("uncommitted changes")

    def test_check_detects_missing_guard(self):
        self.installer("--apply")
        (self.base / ".claude" / "hooks" / "command_guard.py").unlink()
        self.assert_check_fails("does not exist")


if __name__ == "__main__":
    unittest.main()
