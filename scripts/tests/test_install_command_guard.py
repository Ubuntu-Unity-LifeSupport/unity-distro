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

import importlib.util
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

    def real_guard(self, with_installer=True):
        shutil.copy(GUARD, self.guard)
        if with_installer:  # the guard loads the trusted set from the installer beside its checkout
            (self.tmp / "scripts").mkdir(exist_ok=True)
            shutil.copy(INSTALLER, self.tmp / "scripts" / "install_command_guard.py")

    def test_guard_fails_closed_without_the_installer(self):
        """Permission model phase 3: the trusted set is loaded on every call; no
        installer (or an unreadable one) blocks even a harmless command."""
        self.real_guard(with_installer=False)
        result = self.run_handler(json.dumps({"tool_name": "Bash", "tool_input": {"command": "true"}}))
        self.assert_blocked(result, "Command guard failed (FileNotFoundError)")

    def test_guard_loads_the_trusted_set_from_the_installer_source(self):
        """One source: the guard's set equals the installer's, read from the source
        text (a stale bytecode cache beside the installer is never used)."""
        self.real_guard()
        cache = self.tmp / "scripts" / "__pycache__"
        cache.mkdir()
        (cache / "install_command_guard.cpython-314.pyc").write_bytes(b"not bytecode")
        probe = json.dumps({"tool_name": "Bash", "tool_input": {"command": icg.PROBE_TRUSTED_WRITE}})
        self.assert_blocked(self.run_handler(probe), "trusted file")
        spec = importlib.util.spec_from_file_location("guard_under_test", self.guard)
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        self.assertEqual(guard._trusted_set(), (tuple(icg.TRUSTED_FILES), tuple(icg.TRUSTED_DIRS),
                                                tuple(icg.TRUSTED_GLOBS), tuple(icg.SUDOERS_PATHS)))

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
        self.assertEqual(data, icg.proposal({}, Path(DEPLOYED)))

    def test_ask_calibration_http_methods(self):
        """Ask calibration (May, 2026-10-09): a GET through curl -X or gh api -X does
        not ask; POST/PUT/PATCH/DELETE (upper and lower case) ask; data, form and
        upload options and every deny rule are unchanged. The matcher below is the
        documented prefix semantics measured on the installed CLI (case-sensitive,
        the prefix followed by a space, at the start of the command)."""
        ask, deny = icg.PERMISSIONS["ask"], icg.PERMISSIONS["deny"]

        def asks(command):
            for rule in ask:
                body = rule[5:-1]
                if rule.startswith("Bash(") and body.endswith(" *") and (command == body[:-2] or command.startswith(body[:-2] + " ")):
                    return True
            return False

        for broad in ("Bash(curl -X *)", "Bash(curl --request *)", "Bash(gh api -X *)", "Bash(gh api --method *)"):
            self.assertNotIn(broad, ask)
        for command in ("curl -X GET https://example.invalid/", "curl --request GET https://example.invalid/",
                        "gh api -X GET rate_limit", "gh api --method GET rate_limit", "gh api rate_limit",
                        "curl -sSLo /tmp/x https://example.invalid/", "curl -I https://example.invalid/"):
            self.assertFalse(asks(command), command)
        for method in ("POST", "PUT", "PATCH", "DELETE", "post", "put", "patch", "delete"):
            for command in (f"curl -X {method} https://example.invalid/", f"curl --request {method} https://example.invalid/",
                            f"gh api -X {method} repos/x/y", f"gh api --method {method} repos/x/y"):
                self.assertTrue(asks(command), command)
        for command in ("curl -d a=b https://example.invalid/", "curl --data-binary @f https://example.invalid/",
                        "curl -F f=@x https://example.invalid/", "curl -T x https://example.invalid/",
                        "gh api -F a=b repos/x/y", "gh api -f a=b repos/x/y", "gh api --input f repos/x/y",
                        "wget --post-data a=b https://example.invalid/"):
            self.assertTrue(asks(command), command)
        # the accepted residual: mixed case, glued and reordered spellings are outside the rules
        for command in ("curl -X Delete https://example.invalid/", "curl -XPOST https://example.invalid/",
                        "curl -s -X POST https://example.invalid/"):
            self.assertFalse(asks(command), command)
        self.assertEqual(len(deny), 16)
        for rule in ("Bash(aptly publish *)", "Bash(git push --force *)", "Bash(xwd *)", "Edit(//etc/sudoers.d/**)",
                     "Read(//home/claude/.claude/.credentials.json)"):
            self.assertIn(rule, deny)

    def test_permissions_block_forms(self):
        """Permission model phase 3: every rule is an exact command, a ' *' prefix or an absolute path rule."""
        self.assertEqual(icg.rule_form_problems(), [])
        self.assertEqual(icg.PERMISSIONS.get("allow"), None)
        self.assertIn("Bash(aptly publish *)", icg.PERMISSIONS["deny"])
        self.assertIn(f"Edit(//{icg.HOME.lstrip('/')}/.claude/settings.json)", icg.PERMISSIONS["ask"])
        self.assertIn(f"Edit(//{icg.HOME.lstrip('/')}/.claude/settings.json.proposed)", icg.PERMISSIONS["ask"])
        # May's corrections (2026-10-09): no Write(path) rule anywhere (Claude Code never
        # consults one), ~/.claude.json asks, the credentials file is unreadable.
        self.assertEqual([r for r in icg.PERMISSIONS["deny"] + icg.PERMISSIONS["ask"] if r.startswith("Write(")], [])
        self.assertIn(f"Edit(//{icg.HOME.lstrip('/')}/.claude.json)", icg.PERMISSIONS["ask"])
        self.assertIn(f"Read(//{icg.HOME.lstrip('/')}/.claude/.credentials.json)", icg.PERMISSIONS["deny"])
        self.assertIn(f"Edit(//{icg.HOME.lstrip('/')}/.claude/settings.json)", icg.PERMISSIONS["ask"])
        self.assertIn("Edit(//etc/sudoers.d/**)", icg.PERMISSIONS["deny"])
        self.assertNotIn("Bash(gh repo view *)", icg.PERMISSIONS["ask"])
        for rule in icg.PERMISSIONS["deny"] + icg.PERMISSIONS["ask"]:
            if rule.startswith("Bash("):
                self.assertNotRegex(rule, r"\S\*\)$", f"glued wildcard: {rule}")

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
        (self.base / "scripts").mkdir()
        shutil.copy(INSTALLER, self.base / "scripts" / "install_command_guard.py")  # the guard imports the trusted set from it
        (self.base / ".claude" / "settings.json").write_text(icg.dump(icg.proposal({}, self.base)))
        git(self.base, "init", "-q", "-b", "main")
        git(self.base, "add", ".claude", "scripts")
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

    def test_check_detects_catch_all_hook(self):
        self.installer("--apply")
        for matcher in ("*", ".*", ""):
            data = self.data()
            data["hooks"]["PreToolUse"] = data["hooks"]["PreToolUse"][:1] + [
                {"matcher": matcher, "hooks": [{"type": "command", "command": "true"}]}]
            self.settings.write_text(json.dumps(data))
            self.assert_check_fails("another PreToolUse hook also matches Bash")

    def test_apply_refuses_hooks_not_an_object(self):
        self.settings.write_text(json.dumps({"hooks": []}))
        result = self.installer("--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("nothing written", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_backup_keeps_the_first_state(self):
        first = self.settings.read_text()
        self.installer("--apply")
        data = dict(self.data(), theme="light")
        self.settings.write_text(json.dumps(data))
        self.installer("--apply")
        self.assertEqual(self.settings.with_name("settings.json" + icg.BACKUP_SUFFIX).read_text(), first)

    def test_apply_refuses_symlink(self):
        real = self.tmp / "real.json"
        real.write_text(self.settings.read_text())
        self.settings.unlink()
        self.settings.symlink_to(real)
        self.assertEqual(self.installer("--apply").returncode, 1)
        self.assertTrue(self.settings.is_symlink())

    # ---- permission model phase 3 ----------------------------------------------
    def test_propose_writes_the_proposal_and_not_the_settings(self):
        before = self.settings.read_text()
        result = self.installer("--propose")
        self.assertEqual(result.returncode, 0, result.stderr)
        proposed = self.settings.with_name(self.settings.name + icg.PROPOSED_SUFFIX)
        self.assertTrue(proposed.is_file())
        self.assertEqual(oct(proposed.stat().st_mode & 0o777), "0o600")
        self.assertEqual(json.loads(proposed.read_text()), icg.proposal(json.loads(before), self.base))
        self.assertEqual(self.settings.read_text(), before)
        self.assertIn("+  \"permissions\"", result.stdout)
        self.assertIn("Write tool", result.stdout)

    def test_propose_without_the_block(self):
        self.installer("--apply")
        result = self.installer("--propose", "--remove-permissions")
        self.assertEqual(result.returncode, 0, result.stderr)
        proposed = json.loads(self.settings.with_name(self.settings.name + icg.PROPOSED_SUFFIX).read_text())
        self.assertNotIn("permissions", proposed)
        self.assertIn("hooks", proposed)

    def test_apply_refuses_the_live_user_file(self):
        """The installer never writes ~/.claude/settings.json; a path that resolves to it is refused."""
        for spelling in (icg.USER_SETTINGS, Path(str(icg.USER_SETTINGS).replace("/.claude/", "/./.claude/"))):
            with self.subTest(spelling=str(spelling)):
                result = subprocess.run([sys.executable, str(INSTALLER), "--apply", "--settings", str(spelling),
                                         "--base", str(self.base)], capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("live user settings", result.stderr)
        self.assertRaises(PermissionError, icg.write_atomic, icg.USER_SETTINGS, "x")

    def test_apply_writes_the_block_to_a_temporary_file(self):
        self.assertEqual(self.installer("--apply").returncode, 0)
        self.assertEqual(self.data()["permissions"], icg.PERMISSIONS)
        self.assertEqual(self.data()["theme"], "dark")

    def test_abbreviated_options_are_refused(self):
        result = self.installer("--app")
        self.assertEqual(result.returncode, 2)
        self.assertIn("one of the arguments --check --diff --propose --apply is required", result.stderr)
        self.assertEqual(self.settings.read_text().count("permissions"), 0)

    def test_check_detects_missing_or_altered_block(self):
        self.installer("--apply")
        data = self.data()
        del data["permissions"]
        self.settings.write_text(json.dumps(data))
        self.assert_check_fails("permissions block is missing")
        data["permissions"] = dict(icg.PERMISSIONS, deny=icg.PERMISSIONS["deny"][1:])
        self.settings.write_text(json.dumps(data))
        self.assert_check_fails("permissions block is missing or differs")

    def test_check_detects_allow_rules_and_modes(self):
        self.installer("--apply")
        data = self.data()
        data["permissions"] = dict(icg.PERMISSIONS, allow=["Bash(ls *)"])
        self.settings.write_text(json.dumps(data))
        self.assert_check_fails("permissions.allow is not empty")
        data["permissions"] = dict(icg.PERMISSIONS, defaultMode="acceptEdits")
        self.settings.write_text(json.dumps(data))
        self.assert_check_fails("defaultMode")

    def test_check_detects_local_settings(self):
        self.installer("--apply")
        self.settings.with_name("settings.local.json").write_text("{}")
        self.assert_check_fails("settings.local.json")

    def test_check_runs_the_trusted_write_probe(self):
        self.installer("--apply")
        result = self.installer("--check")
        self.assertEqual(result.returncode, 0, result.stdout)
        guard = self.base / ".claude" / "hooks" / "command_guard.py"
        text = guard.read_text()
        self.assertEqual(text.count("found = _write_targets(group, cwd.here)"), 1)
        guard.write_text(text.replace("found = _write_targets(group, cwd.here)", "found = None", 1))
        git(self.base, "commit", "-qam", "weaken rule 1")
        self.assert_check_fails("trusted-write probe")

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
