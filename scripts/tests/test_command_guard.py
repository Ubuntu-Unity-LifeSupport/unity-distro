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


# Relative paths in the corpus resolve against this directory, never against the
# checkout the suite runs from: from the base checkout, .claude/hooks/x.py is a
# trusted write by design (permission model phase 3).
NEUTRAL_CWD = tempfile.gettempdir()


def run_hook(command, env=None, cwd=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd or NEUTRAL_CWD}
    payload = json.dumps(payload)
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

    def test_phase3_trusted_file_writes(self):
        """Permission model phase 3, guard rules 1 and 3: shell writes into
        the trusted files (the set is the installer's) are denied with "use
        Edit"; reads and writes elsewhere are unchanged; sudoers writes and
        visudo are denied in every spelling. Strings are data."""
        home = os.path.expanduser("~")
        denied = {
            "redirect": "echo x >> ~/.claude/settings.json",
            "redirect-absolute": f"echo x > {home}/.claude/settings.json",
            "redirect-home-var": "echo x > $HOME/.claude/settings.json",
            "redirect-proposal": "echo x > ~/.claude/settings.json.proposed",
            "tee": "echo x | tee -a $HOME/.bashrc",
            "cp-destination": "cp /tmp/s.json ~/.claude/settings.json",
            "cp-into-directory": "cp settings.json ~/.claude/",
            "mv-source": "mv ~/.claude/settings.json /tmp/x",
            "rm": "rm ~/.claude/settings.json",
            "rm-r-ancestor": "rm -r ~/.claude",
            "sed-i": "sed -i s/a/b/ ~/.gitconfig",
            "gzip": "gzip ~/.claude/settings.json",
            "curl-o": "curl -o ~/.claude/settings.json https://example.invalid/y",
            "ln-hard": "ln -f /tmp/x ~/.claude/settings.json",
            "python-c-open-w": "python3 -c \"open('" + home + "/.claude/settings.json','w').write('x')\"",
            "python-heredoc-open-w": "python3 - <<'EOF'\nopen('" + home + "/.claude/settings.json','w').write('x')\nEOF",
            "python-heredoc-shutil": "python3 - <<'EOF'\nimport shutil\nshutil.copy('/tmp/x', '" + home + "/.claude/settings.json')\nEOF",
            "ssh-key": "cp /tmp/k ~/.ssh/id_ed25519",
            "base-script": "cp x.py ~/unity-distro/scripts/taskctl.py",
            "base-hook-dir": "cp x.py ~/unity-distro/.claude/hooks/command_guard.py",
            "skills": "cp x.md ~/.claude/skills/x/SKILL.md",
            "shell-body": "bash <<'EOF'\ncp /tmp/s.json ~/.claude/settings.json\nEOF",
            "visudo": "sudo visudo -c",
            "visudo-bare": "visudo",
            "sudoers-tee": "echo x | sudo tee /etc/sudoers.d/x",
            "sudoers-cp": "sudo cp f /etc/sudoers.d/",
            "sudoers-rm": "sudo rm /etc/sudoers.d/x",
        }
        allowed = {
            "cat": "cat ~/.claude/settings.json",
            "grep": "grep -n hooks ~/.claude/settings.json",
            "diff": "diff ~/.claude/settings.json /tmp/x",
            "cp-source": "cp ~/.claude/settings.json /tmp/backup.json",
            "python-read-report": "python3 - <<'EOF'\ns=open('" + home + "/.claude/settings.json').read()\nopen('/tmp/report.txt','w').write(s)\nEOF",
            "sudoers-cat": "sudo cat /etc/sudoers.d/99-claude-nopasswd",
            "worktree-settings": "echo x >> ~/work/b/unity-distro/.claude/settings.json",
            "worktree-script": "cp x.py ~/work/a/unity-distro/scripts/taskctl.py",
            "ssh-config": "echo host >> ~/.ssh/config",
            "docs": "cp x.md ~/unity-distro/docs/research/notes.md",
            "cp-into-docs-dir": "cp new.py ~/unity-distro/docs/",
            "installer-check": "python3 ~/unity-distro/scripts/install_command_guard.py --check",
            "installer-propose": "python3 scripts/install_command_guard.py --propose",
            "git-add-installer": "git add scripts/install_command_guard.py",
            "pycache-cleanup": "rm -r -- ~/unity-distro/.claude/hooks/__pycache__",
            "chmod-trusted": "chmod g-w ~/.aptly.conf",
        }
        # Verifier findings on the first implementation (2026-10-09): shell -c
        # strings, a leading cd, >|, downloads and archives into a directory,
        # the wrappers Claude Code strips, sed option clusters. (command, cwd)
        denied.update({
            "sh-c-sudoers": ("sudo sh -c 'echo x >> /etc/sudoers'", None),
            "bash-c-sudoers-d": ("sudo bash -c \"echo 'claude ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/claude\"", None),
            "sh-c-settings": ("sh -c 'echo x > ~/.claude/settings.json'", None),
            "bash-ec-cp": ("bash -ec 'cp /tmp/s.json ~/.claude/settings.json'", None),
            "sh-c-nested": ("sh -c 'sh -c \"echo x > ~/.claude/settings.json\"'", None),
            "cd-redirect": ("cd ~/.claude && echo x > settings.json", None),
            "cd-cp": ("cd ~/.claude && cp /tmp/s.json settings.json", None),
            "cd-subshell": ("(cd ~/.claude && echo x > settings.json)", None),
            "cd-semicolon-sed": ("cd ~/.claude; sed -i s/a/b/ settings.json", None),
            "cd-relative-chain": ("cd unity-distro && cd scripts && cp /tmp/x taskctl.py", home),
            "cwd-relative": ("echo x >> settings.json", home + "/.claude"),
            "cwd-dotdot": ("cp /tmp/x ../.claude/settings.json", home + "/.ssh"),
            "clobber": ("echo x >| ~/.claude/settings.json", None),
            "clobber-fd": ("echo x 1>| ~/.claude/settings.json", None),
            "curl-O-cwd": ("curl -O https://example.invalid/settings.json", home + "/.claude"),
            "curl-sLO-cwd": ("curl -sLO https://example.invalid/settings.json", home + "/.claude"),
            "curl-remote-name-cd": ("cd ~/.claude && curl --remote-name https://example.invalid/settings.json", None),
            "wget-P-dir": ("wget -P ~/.claude https://example.invalid/settings.json", None),
            "wget-cwd": ("wget https://example.invalid/settings.json", home + "/.claude"),
            "wget-P-skills": ("wget -P ~/.claude/skills/x https://example.invalid/SKILL.md", None),
            "unzip-d": ("unzip -d ~/.claude a.zip", None),
            "unzip-d-plugins": ("unzip a.zip -d ~/.claude/plugins", None),
            "unzip-cwd": ("unzip a.zip", home + "/.claude"),
            "tar-old-style-C": ("tar xf a.tar -C ~/.claude", None),
            "tar-directory-eq": ("tar -xf a.tar --directory=$HOME/.claude", None),
            "tar-extract-directory": ("tar --extract -f a.tar --directory ~/.gnupg", None),
            "tar-x-C": ("tar -x -f a.tar -C ~/.claude", None),
            "tar-cwd": ("tar xzf a.tgz", home + "/.claude"),
            "timeout-cp": ("timeout 5 cp /tmp/x ~/.claude/settings.json", None),
            "timeout-s-cp": ("timeout -s KILL 20 cp /tmp/x ~/.claude/settings.json", None),
            "nice-tee": ("echo x | nice -n 10 tee ~/.bashrc", None),
            "nohup-sh-c": ("nohup sh -c 'echo x > ~/.claude/settings.json' &", None),
            "sed-Ei": ("sed -Ei 's/a/b/' ~/.gitconfig", None),
            "sed-ri": ("sed -ri 's/a/b/' ~/.gitconfig", None),
            "sed-i-suffix": ("sed -i.bak s/a/b/ ~/.gitconfig", None),
            "python-c-cd": ("cd ~/.claude && python3 -c \"open('settings.json','w').write('x')\"", None),
            "python-Bc": ("python3 -Bc \"open('" + home + "/.claude/settings.json','a').write('x')\"", None),
        })
        allowed.update({
            "cd-elsewhere": ("cd ~/work && echo x > settings.json", None),
            "cd-subshell-ends": ("(cd ~/.claude && cat settings.json); echo x > settings.json", home + "/work"),
            "cd-unknown-var": ("cd $D && echo x > settings.json", None),
            "cd-dash": ("cd - && echo x > settings.json", home + "/.claude"),
            "cd-home-then-work": ("cd && cd work && echo x > settings.json", None),
            "sh-c-reader": ("sh -c 'cat ~/.claude/settings.json'", None),
            "sh-c-elsewhere": ("bash -c 'echo x > /tmp/out.txt'", None),
            "sh-c-apostrophe": ("bash -c 'echo \"it'\"'\"'s fine\"'", None),
            "clobber-elsewhere": ("echo x >| /tmp/out.txt", None),
            "curl-O-elsewhere": ("curl -O https://example.invalid/settings.json", home + "/work"),
            "curl-O-in-base": ("curl -sO https://example.invalid/x.tar.gz", home + "/unity-distro"),
            "wget-elsewhere": ("wget -P /tmp https://example.invalid/settings.json", None),
            "wget-stdout-pipe": ("wget -O - https://example.invalid/x | tar xz -C /tmp", None),
            "tar-create-exclude-C": ("tar -czf /tmp/b.tgz --exclude=cache -C ~/.claude .", None),
            "tar-list": ("tar tf a.tar", None),
            "tar-extract-in-base": ("tar xf a.tar", home + "/unity-distro"),
            "tar-extract-in-packages": ("tar xJf a.tar.xz -C packages/compiz", home + "/unity-distro"),
            "unzip-elsewhere": ("unzip -d /tmp/x a.zip", None),
            "unzip-in-worktree": ("unzip a.zip", home + "/work/b/unity-distro"),
            "timeout-reader": ("timeout 5 cat ~/.claude/settings.json", None),
            "timeout-cp-elsewhere": ("timeout -s KILL 20 cp /tmp/x /tmp/y", None),
            "sed-E-stdout": ("sed -E 's/a/b/' ~/.gitconfig", None),
            "sed-n-p": ("sed -n 1,5p ~/.gitconfig", None),
            "git-status-in-claude": ("git status", home + "/.claude"),
            "pushd-reader": ("pushd ~/.claude && cat settings.json && popd", None),
            "python-report-cd": ("cd ~/.claude && python3 -c \"print(open('settings.json').read())\"", None),
        })
        # Verifier round 2: the directory follows into heredoc bodies, a leading
        # shell word hides neither cd nor a writer, su -c is a shell string,
        # pushd/popd is a stack; ~ is not a directory one extracts into.
        denied.update({
            "cd-bash-heredoc": ("cd ~/.claude && bash <<'EOF'\necho x > settings.json\nEOF", None),
            "cd-sh-heredoc-cp": ("cd ~/.claude; sh <<'EOF'\ncp /tmp/s.json settings.json\nEOF", None),
            "cd-python-heredoc": ("cd ~/.claude && python3 - <<'EOF'\nopen('settings.json','w').write('x')\nEOF", None),
            "heredoc-cd-inside": ("bash <<'EOF'\ncd ~/.claude\necho x > settings.json\nEOF", None),
            "brace-cd": ("{ cd ~/.claude; echo x > settings.json; }", None),
            "if-cd": ("if cd ~/.claude; then echo x > settings.json; fi", None),
            "if-cp": ("if cp /tmp/s.json ~/.claude/settings.json; then echo ok; fi", None),
            "while-tee": ("while true; do echo x | tee -a ~/.bashrc; done", None),
            "su-c-sudoers-d": ("sudo su -c 'echo x > /etc/sudoers.d/x'", None),
            "su-root-c-sudoers": ("su root -c 'echo x >> /etc/sudoers'", None),
            "sudo-bash-heredoc-sudoers": ("sudo bash <<'EOF'\necho x > /etc/sudoers.d/claude\nEOF", None),
            "pushd-write": ("pushd ~/.claude && echo x > settings.json && popd", None),
            "wget-qO-file": ("wget -qO ~/.claude/settings.json https://example.invalid/x", None),
        })
        allowed.update({
            "cd-heredoc-elsewhere": ("cd /tmp && bash <<'EOF'\necho x > settings.json\nEOF", home + "/.claude"),
            "heredoc-cd-out": ("bash <<'EOF'\ncd /tmp\necho x > settings.json\nEOF", home + "/.claude"),
            "brace-reader": ("{ cd ~/.claude; cat settings.json; }", None),
            "pushd-popd-then-write": ("pushd ~/.claude && cat settings.json && popd && echo x > settings.json", home + "/work"),
            "tar-xf-in-home": ("tar xf a.tar", home),
            "tar-C-home": ("tar -xf a.tar -C ~", None),
            "wget-qO-dash": ("wget -qO- https://example.invalid/x | head", home + "/.claude"),
            "su-c-reader": ("sudo su -c 'cat /etc/sudoers.d/x'", None),
            "cd-base-git": ("cd ~/unity-distro && git status && git add scripts/x.py && git commit -q -m x", None),
            "ssh-remote-sudoers": ("ssh target 'echo x | sudo tee /etc/sudoers.d/x'", None),
            "cat-heredoc-data": ("cat > /tmp/x <<'EOF'\necho x > ~/.claude/settings.json\nEOF", None),
            "fd-dup-in-claude": ("ls 2>&1 | head", home + "/.claude"),
        })
        # Verifier round 3: a body is walked by its runner - the owner, sudo -s/-i
        # alone, or the next command of a pipeline - never as data.
        denied.update({
            "cat-pipe-bash": ("cat <<'EOF' | bash\necho x > ~/.claude/settings.json\nEOF", None),
            "cat-pipe-sudo-bash-sudoers": ("cat <<'EOF' | sudo bash\necho x > /etc/sudoers.d/x\nEOF", None),
            "cat-pipe-sh-s": ("cat <<'EOF' | sh -s\ncp /tmp/x ~/.claude/settings.json\nEOF", None),
            "sudo-s-heredoc-sudoers": ("sudo -s <<'EOF'\necho x > /etc/sudoers.d/x\nEOF", None),
            "sudo-i-heredoc-sudoers": ("sudo -i <<'EOF'\necho x > /etc/sudoers.d/x\nEOF", None),
            "cat-pipe-python": ("cat <<'EOF' | python3\nopen('" + home + "/.claude/settings.json','w').write('x')\nEOF", None),
            "cd-cat-pipe-bash": ("cd ~/.claude && cat <<'EOF' | bash\necho x > settings.json\nEOF", None),
            # Verifier round 4: a passthrough between the heredoc and the shell
            "claude-json": ("echo '{}' > ~/.claude.json", None),  # May's correction: ~/.claude.json is trusted
            "cat-pipe-tee-pipe-bash": ("cat <<'EOF' | tee /tmp/s.sh | bash\ncp /tmp/x ~/.claude/settings.json\nEOF", None),
            "cat-pipe-sed-pipe-sudo-bash": ("cat <<'EOF' | sed s/X/x/ | sudo bash\necho X > /etc/sudoers.d/x\nEOF", None),
        })
        allowed.update({
            "cat-pipe-grep-data": ("cat <<'EOF' | grep settings\necho x > ~/.claude/settings.json\nEOF", None),
            "cat-to-file-data": ("cat <<'EOF' > /tmp/notes.txt\nsudo -s\necho x > /etc/sudoers.d/x\nEOF", None),
            "cat-pipe-bash-reader": ("cat <<'EOF' | bash\ncat ~/.claude/settings.json\nEOF", None),
            "cat-pipe-ssh-remote": ("cat <<'EOF' | ssh target bash\necho x > /etc/sudoers.d/x\nEOF", None),
            "git-commit-F-message": ("git commit -F - <<'EOF'\nfix: stop writing ~/.claude/settings.json from the shell\nEOF", None),
            "cd-work-bash-heredoc-relative": ("cd ~/work/b/unity-distro && bash <<'EOF'\necho x > .claude/settings.json\nEOF", home),
            "claude-json-read": ("python3 -c \"import json; json.load(open('" + home + "/.claude.json'))\"", None),
            "cat-pipe-tee-pipe-grep": ("cat <<'EOF' | tee /tmp/s.sh | grep x\ncp /tmp/x ~/.claude/settings.json\nEOF", None),
        })
        for key, command in sorted(denied.items()):
            command, cwd = command if isinstance(command, tuple) else (command, None)
            with self.subTest(denied=key):
                result = run_hook(command, cwd=cwd)
                self.assertEqual(result.returncode, 2, f"{key} allowed")
                self.assertIn("trusted file" if "sudo" not in key else "sudoers", result.stderr)
        for key, command in sorted(allowed.items()):
            command, cwd = command if isinstance(command, tuple) else (command, None)
            with self.subTest(allowed=key):
                result = run_hook(command, cwd=cwd)
                self.assertEqual(result.returncode, 0, f"{key} denied: {result.stderr}")

    def test_other_rules_unchanged(self):
        for command in ("git add -A", "git push --force origin x", "xwd -root",
                        "pkill -f compiz", "rm -rf $X/y", "true\ngit push --force origin x",
                        "true\nrm -rf $X/y"):
            with self.subTest(command=command):
                self.assertEqual(run_hook(command).returncode, 2)


if __name__ == "__main__":
    unittest.main()
