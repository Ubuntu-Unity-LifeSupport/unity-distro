#!/usr/bin/env python3
"""Regression tests for .claude/hooks/command_guard.py (UNITY-20260927-058).

The hook is run as Claude Code runs it: a PreToolUse JSON payload on stdin,
exit status 2 and a message on stderr to deny, 0 to allow. Every form that
reaches aptly's `publish` command (or runs aptly commands it cannot inspect)
must be denied; ordinary aptly reads and unrelated commands must pass.
Run: python3 -m unittest discover -s scripts/tests
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "command_guard.py"
CFG = "/tmp/claude-1000/x/scratchpad/aptly047/aptly.conf"

DENIED = [
    # control: the form the hook always blocked
    "aptly publish list",
    "aptly publish show resolute",
    # global flags before the command (the reported bypass)
    f"aptly -config={CFG} publish list",
    f"aptly -config {CFG} publish list",
    f"aptly --config={CFG} publish list",
    f"aptly --config {CFG} publish list",
    "aptly -config=/home/claude/.aptly.conf publish drop resolute",
    "aptly -config=../../home/claude/.aptly.conf publish drop resolute",
    "aptly -architectures=amd64 -config=x.conf publish drop resolute",
    "aptly -architectures amd64 publish list",
    "aptly -dep-follow-source publish list",
    "aptly -dep-follow-source=true -config x publish list",
    "aptly -config=x -- publish list",
    "aptly 'publish' list",
    "aptly pub\\lish list",
    # environment and wrappers
    "HOME=/tmp aptly publish list",
    "HOME=/tmp aptly -config=x publish list",
    "env HOME=/tmp aptly publish list",
    "env -i HOME=/tmp aptly publish list",
    "APTLY_CONFIG=/tmp/x.conf aptly publish list",
    "sudo -u claude aptly -config=x publish list",
    "sudo -E aptly publish list",
    "command aptly -config x publish list",
    "exec aptly -config=x publish list",
    "/usr/bin/aptly -config=x publish list",
    "/usr/bin/../bin/aptly publish list",
    "timeout 60 aptly -config=x publish list",
    "nice -n 5 aptly publish list",
    "nohup aptly -config=x publish list",
    "setsid aptly publish list",
    "stdbuf -oL aptly publish list",
    "echo resolute | xargs aptly -config=x publish drop",
    "true && aptly -config=x publish list",
    "cd /srv && aptly publish list",
    # nested shells and command substitution
    "bash -c 'aptly -config=x publish list'",
    "sh -c \"aptly publish list\"",
    "bash -lc 'aptly -config x publish list'",
    "eval 'aptly -config=x publish list'",
    "echo \"$(aptly -config=x publish list)\"",
    "echo $(aptly -config=x publish list)",
    "echo `aptly -config=x publish list`",
    "(aptly -config=x publish list)",
    "{ aptly -config=x publish list; }",
    # aptly commands that run other aptly commands or serve the publishing API
    "aptly task run publish drop resolute",
    "aptly -config=x task run -filename=cmds.txt",
    "aptly task run",
    "aptly api serve -listen=127.0.0.1:8080",
    "aptly -config=x api serve",
    # copies or links of the aptly binary under another name
    "ln -s /usr/bin/aptly /tmp/a && /tmp/a publish list",
    "cp /usr/bin/aptly ./tool",
    "install -m755 /usr/bin/aptly ./tool",
    # design review round 1: newlines, expansion, xargs/find, external subcommands
    "true\naptly publish list",
    "true\naptly -config=x publish list",
    "aptly -config=x \\\npublish list",
    "aptly $'publish' list",
    "aptly {publish,} list",
    "p=publish; aptly $p list",
    "aptly publis? list",
    "f(){ aptly \"$@\"; }; f publish list",
    "echo publish list | xargs aptly",
    "echo publish list | xargs -n2 aptly -config=x",
    "find . -name publish -exec aptly {} list \\;",
    "aptly foo",
    "aptly",
    # quoted scripts run by other programs
    "su claude -c 'aptly publish list'",
    "ssh localhost 'aptly -config=x publish list'",
    "runuser -u claude -- sh -c 'aptly publish list'",
    "script -qc 'aptly publish list' /dev/null",
    "flock /tmp/l -c 'aptly -config=x publish list'",
    "watch -n1 'aptly publish list'",
    "tmux new -d 'aptly publish list'",
    "python3 -c \"import os; os.system('aptly -config=x publish list')\"",
    "bash <<'EOF'\naptly -config=x publish list\nEOF",
    "python3 - <<'EOF'\nimport subprocess\nsubprocess.run('aptly publish list', shell=True)\nEOF",
    "cat > /tmp/x <<EOF\n$(aptly -config=x publish list)\nEOF",
    "aptly task run <<'EOF'\npublish list\nEOF",
    # design review round 2: readers that run strings, wrappers, heredoc parsing
    "git -c core.pager='aptly publish list' log",
    "git -c alias.p='!aptly -config=x publish list' p",
    "GIT_PAGER='aptly publish list' git log",
    "dpkg --pre-invoke='aptly publish list' -l",
    "apt-get -o 'APT::Update::Pre-Invoke::=aptly publish list' update",
    "LESSOPEN='|aptly publish list %s' less f",
    "rg --pre 'aptly' publish",
    "git bisect run aptly $p",
    "nsenter -t 1 -m aptly -config=x publish list",
    "chroot / aptly publish list",
    "systemd-run --user aptly publish list",
    "echo \"a <<X\"\naptly publish list\nX",
    "cat <<EOF | bash\naptly -config=x publish list\nEOF",
    "cat <<'EOF' |\naptly -config=x publish list\nEOF\nbash",
    "sh <<'A' <<'B'\nx\nA\naptly publish list\nB\n",
    "cat <<\"E\" | sh\naptly publish list\nE",
    "cat <<E'O'F | sh\naptly publish list\nEOF",
    "cat <<\\EOF | sh\naptly publish list\nEOF",
    "sh<<EOF\naptly publish list\nEOF",
    "sh <<-EOF\n\taptly publish list\n\tEOF",
    "cat <<<'x'\naptly publish list",
    "echo \"it's $(aptly -config=x publish list)\"",
    "cat /usr/bin/aptly > /tmp/t && chmod +x /tmp/t && /tmp/t repo list",
    "tee /tmp/t < /usr/bin/aptly",
    "ln -s /usr/bin/apt?y ~/.local/bin/zz",
    "ln -s /usr/bin/a?tly ~/.local/bin/zz",
    "/usr/bin/[a]ptly repo list; ln /usr/*/?ptly x",
    # design review round 3: aptly without the word, executed heredocs, writing readers
    "{apt,-architectures=}ly publish drop resolute",
    "/usr/bin/apt?y publish list",
    "$'\\x61ptly' publish list",
    "$'\\x61ptly' $'\\x70ublish' list",
    "a=apt; ${a}ly publish list",
    "$(printf apt)ly publish list",
    "bash -c \"$(cat <<'EOF'\naptly publish list\nEOF\n)\"",
    "eval \"$(cat <<'EOF'\naptly -config=x publish list\nEOF\n)\"",
    "cat > /tmp/s.sh <<'EOF'\naptly publish list\nEOF\nbash /tmp/s.sh",
    "git grep -O'aptly $(printf pub)lish list' x",
    "sort --compress-program=aptly f",
    "aptly version; bash -c 'aptly $(printf pub)lish list'",
    "python3 - <<'EOF'\nprint(\"it's\"); import os; os.system('aptly -config=x publish list')\nEOF",
    # implementation review: pipes into a shell, flags that eat the command word, copies via readers
    "echo 'aptly ${a}lish list' | sh",
    "aptly -distribution repo publish list",
    "grep -a '' /usr/bin/aptly > /tmp/t",
    "head -c 99999999 /usr/bin/aptly > /tmp/t",
    "X=$(cat <<'EOF'\naptly publish list\nEOF\n); bash -c \"$X\"",
    "perl <<'EOF'\nprint `aptly publish list`;\nEOF",
    "python3 - <<'EOF'\nimport subprocess; subprocess.run(['aptly', 'publish', 'list'])\nEOF",
    # accepted false positives (fail closed), see README "Known false positives"
    "timeout 60 aptly repo list",
    "aptly -architectures amd64 snapshot list",
    "dpkg -L aptly",
    "apt-get source aptly",
]

ALLOWED = [
    # readers only: nothing runs, so the words and mentions do not matter
    "python3 - <<'EOF'\np='docs/x.md'; s=open(p).read()\ns=s.replace('`aptly publish` is blocked', 'x')\nopen(p,'w').write(s)\nEOF",
    "{ echo \"# aptly snapshot notes\"; ls /srv/aptly/public; } > /tmp/notes.txt",
    "until aptly repo search unity-resolute 'x' >/dev/null 2>&1 && ! pgrep -x aptly >/dev/null; do sleep 10; done",
    "aptly repo search -format='{{.Package}}' unity-resolute | python3 -c 'import sys; print(len(sys.stdin.read()))'",
    "python3 scripts/safe_git.py stage --repo . a && git commit -m \"$(cat <<'EOF'\nit's aptly\nEOF\n)\"",
    "grep -n publish \"$f\"",
    "grep -rn 'aptly publish' docs",
    "grep -rn 'aptly[ ]publish' docs",
    "git commit -m 'docs: aptly publish switch notes'",
    "grep -n aptly f > /tmp/out",
    "echo \"$(date -u +'%F %H:%MZ') B DONE publish decision; task moved, +unity1 in aptly\" >> ~/AGENTS-LOG.md",
    "cp -a /srv/aptly/db /tmp/backup-db",
    "cp /srv/aptly/public/unity-distro-archive.asc /tmp/x",
    "ls /srv/aptly/public; ls -d /srv/aptly",
    "pgrep -a -x aptly",
    "aptly -config=x repo list && echo \"done aptly\"",
    "aptly version",
    "aptly repo show unity-resolute",
    f"aptly -config={CFG} snapshot list",
    f"aptly -config {CFG} repo list",
    "aptly snapshot search -format '{{.Key}}' snap 'Name (x)'",
    "aptly -architectures=amd64 snapshot show snap",
    "aptly serve -listen=127.0.0.1:8080",
    "aptly config show",
    "grep -n aptly scripts/publish_aptly.py",
    "grep -n aptly scripts/apt_view.py | head -3",
    "apt-cache policy aptly",
    "dpkg-query -L aptly",
    "ls /usr/bin/aptly 2>/dev/null",
    "git commit -m 'docs: aptly snapshot notes'",
    "cat > docs/y.md <<-'EOF'\n\tRun aptly publish switch only via publish_aptly.py.\n\tEOF",
    "git commit -m \"$(cat <<'EOF'\ndocs: note on aptly publish\n\naptly -config=x publish list is blocked\nEOF\n)\"",
    "cat > docs/x.md <<'EOF'\nRun aptly publish switch only via publish_aptly.py.\naptly -config=x publish list\nEOF",
    "aptly -config=x repo list\naptly snapshot list",
    "cat <<'A' <<'B'\nx\nA\naptly publish list is text here\nB\n",
    # a commit next to a non-reader: the body is read as a script, for the aptly rules only
    "python3 scripts/safe_git.py stage --repo . a.txt && git commit -m \"$(cat <<'EOF'\nscripts: don't push --force; git add -A is blocked\nEOF\n)\"",
    "python3 scripts/publish_aptly.py --help",
    # UNITY-20261008-004: the repository database backup (a directory name ending in /aptly is denied)
    "python3 scripts/backup_aptly_db.py --task UNITY-20261008-004",
    "python3 scripts/backup_aptly_db.py ~/backups/repo-20261008-004",
    "cat ~/.aptly.conf",
    "git commit -m 'scripts: publish_aptly.py records the switch'",
    "echo publish",
    "ls /usr/bin/aptly",
    "sha256sum /usr/bin/aptly",
    "HOME=/tmp ls",
]


def run_hook(command, env=None):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True,
                          text=True, env=env)


class AptlyPublishGuardTest(unittest.TestCase):
    def test_denied(self):
        for command in DENIED:
            with self.subTest(command=command):
                result = run_hook(command)
                self.assertEqual(result.returncode, 2, f"allowed: {command}")
                self.assertTrue(result.stderr.strip())

    def test_allowed(self):
        for command in ALLOWED:
            with self.subTest(command=command):
                result = run_hook(command)
                self.assertEqual(result.returncode, 0, f"denied: {command}: {result.stderr}")

    def test_symlink_to_aptly(self):
        """A pre-existing link to the aptly binary under another name is aptly."""
        real = "/usr/bin/aptly"
        if not os.path.exists(real):
            self.skipTest("aptly not installed")
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "tool"
            link.symlink_to(real)
            for command in (f"{link} publish list", f"{link} -config=x publish list"):
                with self.subTest(command=command):
                    self.assertEqual(run_hook(command).returncode, 2)
            self.assertEqual(run_hook(f"{link} repo list").returncode, 0)

    def test_hard_link_to_aptly(self):
        """Identity by device and inode: a hard link is aptly whatever its name.

        A stand-in aptly on PATH (the hook resolves aptly through PATH) and a
        hard link to it in the same directory; nothing is executed."""
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "aptly"
            fake.write_text("#!/bin/sh\nexit 1\n")
            fake.chmod(0o755)
            link = Path(tmp) / "tool"
            os.link(fake, link)
            env = dict(os.environ, PATH=f"{tmp}:{os.environ['PATH']}")
            self.assertEqual(run_hook(f"{link} publish list", env).returncode, 2)
            self.assertEqual(run_hook(f"{link} -config=x publish list", env).returncode, 2)
            self.assertEqual(run_hook(f"{link} repo list", env).returncode, 0)

    def test_monitor_tool(self):
        """Monitor runs shell commands too; a WebSocket-only Monitor has no shell."""
        def run(tool_input):
            payload = json.dumps({"tool_name": "Monitor", "tool_input": tool_input})
            return subprocess.run([sys.executable, str(HOOK)], input=payload,
                                  capture_output=True, text=True)
        self.assertEqual(run({"command": "aptly -config=x publish list", "description": "d",
                              "timeout_ms": 1000}).returncode, 2)
        self.assertEqual(run({"command": "tail -f /tmp/log", "description": "d",
                              "timeout_ms": 1000}).returncode, 0)
        self.assertEqual(run({"ws": {"url": "wss://example.invalid/s"}, "description": "d",
                              "timeout_ms": 1000}).returncode, 0)
        self.assertEqual(run({"description": "d", "timeout_ms": 1000}).returncode, 2)

    def test_settings_register_monitor(self):
        settings = json.loads((HOOK.parents[1] / "settings.json").read_text())
        matchers = {entry["matcher"] for entry in settings["hooks"]["PreToolUse"]
                    if any("command_guard.py" in h["command"] for h in entry["hooks"])}
        self.assertEqual(matchers, {"Bash|Monitor"})

    def test_heredoc_text_only_when_nothing_runs_it(self):
        """UNITY-20260929-018: a heredoc body the shell (or git) may run is not text.

        The forms are the Design Challenger's probes (data file). Keys starting
        with "ok-" are ordinary writes that must stay allowed; "ctl-" keys are
        controls with nothing forbidden in the body; every other key must be denied."""
        forms = json.loads((Path(__file__).parent / "data" / "command_guard_018_must_deny.json").read_text())
        self.assertGreaterEqual(len([k for k in forms if not k.startswith(("ok-", "ctl-"))]), 20)
        for key, command in sorted(forms.items()):
            with self.subTest(form=key):
                result = run_hook(command)
                if key.startswith("ok-"):
                    self.assertEqual(result.returncode, 0, f"{key} denied: {result.stderr}")
                elif not key.startswith("ctl-"):
                    self.assertEqual(result.returncode, 2, f"{key} allowed")

    def test_phase1_false_positive_cases(self):
        """Permission model phase 1 (UNITY-20260929-003): the Design Challenger
        probes of rounds 1-8 and the corpus RC1/RC1b minimal forms, each with
        its verdict under the phase-1 guard (data file; strings never pass
        through a shell). Nothing the guard denied before may be allowed except
        the enumerated RC1/RC1b/RC4 forms and the three recorded harmless cases."""
        data = json.loads((Path(__file__).parent / "data" / "command_guard_003_cases.json").read_text())
        self.assertGreaterEqual(len(data["allowed"]), 100)
        self.assertGreaterEqual(len(data["denied"]), 130)
        for key, command in sorted(data["denied"].items()):
            with self.subTest(denied=key):
                self.assertEqual(run_hook(command).returncode, 2, f"{key} allowed")
        for key, command in sorted(data["allowed"].items()):
            with self.subTest(allowed=key):
                result = run_hook(command)
                self.assertEqual(result.returncode, 0, f"{key} denied: {result.stderr}")

    def test_phase1_apostrophe_heredoc_bodies(self):
        """RC1: a quoted-delimiter heredoc body with an apostrophe is decided,
        not refused; the rules still see the lines of the body."""
        allowed = [
            "cat > /tmp/notes.md <<'EOF'\nIt's a note about May's decision.\nEOF",
            "python3 - <<'EOF'\nprint(\"it's fine\")\nEOF",
            "git commit -F - <<'EOF'\ndocs: it's done\n\nA commit message with an apostrophe.\nEOF",
            "git -c user.name=x commit -F - -q -s <<'EOF'\nit's\nEOF",
        ]
        denied = [
            "bash <<'EOF'\necho it's\npkill -f compiz\nEOF",
            "sh <<'EOF'\necho it's\nrm -rf $X/y\nEOF",
            "cat <<'EOF'\nit's\ngit add -A\nEOF",
            "bash <<'EOF'\necho it's\necho '\"' && pkill -f x && echo '\"'\nEOF",
            "bash <<'EOF'\necho it's\nrm -rf /tmp/a \";$X/y\"\nEOF",
            "bash <<'EOF'\necho it's\ngit add \";-A\"\nEOF",
            "cat <<'EOF'\nit's\n\"unterminated\nEOF",
        ]
        for command in allowed:
            with self.subTest(allowed=command[:40]):
                result = run_hook(command)
                self.assertEqual(result.returncode, 0, result.stderr)
        for command in denied:
            with self.subTest(denied=command[:40]):
                self.assertEqual(run_hook(command).returncode, 2)

    def test_phase1_git_commit_stdin_message_is_text(self):
        """RC1b: a message read from stdin is never run by git, so a line that
        names a blocked operation is text; an editor, template or -a keeps it a script."""
        body = "\n".join(["docs: note", "", "Never run: aptly publish list", "nor pkill -f x", "EOF"])
        self.assertEqual(run_hook("git commit -F - <<'EOF'\n" + body).returncode, 0)
        self.assertEqual(run_hook("git commit --file=- --no-verify <<'EOF'\n" + body).returncode, 0)
        for form in ("git commit -F - -e <<'EOF'\n", "git commit -a -F - <<'EOF'\n",
                     "git -c core.editor=vi commit -F - <<'EOF'\n", "git commit -F - -t tmpl <<'EOF'\n"):
            with self.subTest(form=form):
                self.assertEqual(run_hook(form + body).returncode, 2)

    def test_phase1_sed_substitution_is_a_reader(self):
        """RC4: one s/// script on an existing file is a read-only tool for
        the aptly rules; e, w, -e, -i.bak and the aptly binary as operand are not."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "notes.md"
            target.write_text("a\n")
            # corpus record 11's shape: a reader writes a line that mentions aptly
            # into a file, then sed edits that file. With sed a reader, nothing runs.
            write = f"printf '%s\\n' '- note: aptly repo show' >> {target} && "
            allowed = [write + f"sed -i 's/a/b/' {target}", write + f"sed -i -E 's/a (b)/\\1/g' {target}",
                       write + f"sed -n 's|x|y|p' {target}"]
            denied = [write + f"sed -e 's/a/b/' {target}", write + f"sed -i.bak 's/a/b/' {target}",
                      write + f"sed 's/a/b/w {tmp}/f' {target}", write + f"sed -i 's/x/y/e' {target}",
                      write + f"sed -i 's/a/aptly/' {target}",
                      f"printf '%s\\n' '- note: aptly repo show' >> {tmp}/missing && sed -i 's/a/b/' {tmp}/missing",
                      "sed -i 's/a/b/' /usr/bin/aptly"]
            for command in allowed:
                with self.subTest(allowed=command[:50]):
                    result = run_hook(command)
                    self.assertEqual(result.returncode, 0, result.stderr)
            for command in denied:
                with self.subTest(denied=command[:50]):
                    self.assertEqual(run_hook(command).returncode, 2)

    def test_other_rules_unchanged(self):
        for command in ("git add -A", "git push --force origin x", "xwd -root",
                        "pkill -f compiz", "rm -rf $X/y", "true\ngit push --force origin x",
                        "true\nrm -rf $X/y"):
            with self.subTest(command=command):
                self.assertEqual(run_hook(command).returncode, 2)


if __name__ == "__main__":
    unittest.main()
