#!/usr/bin/env python3
"""Feed the command examples of the project's docs to the guard (UNITY-20260927-058, part F).

Every fenced shell block in the listed documents is passed to the hook as
JSON on stdin, one block at a time; nothing is executed. The
workflows documented there must pass. The forms that section 9 and the card
describe as allowed or denied are checked as listed in DOCUMENTED.
Usage: doc_examples.py HOOK
"""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
DOCS = ["docs/ENGINEERING-PROCESS.md", "docs/TWO-AGENTS.md", "docs/COORDINATOR.md", "CLAUDE.md",
        *sorted(str(p.relative_to(ROOT)) for p in (ROOT / ".claude/skills").glob("*/SKILL.md"))]
SHELL_LANGS = {"", "bash", "sh", "shell", "console"}


def shell_blocks(text):
    """(line, block) for fenced blocks whose language is a shell or unset; fences pair up."""
    lines, n = text.splitlines(), 0
    while n < len(lines):
        if lines[n].startswith("```"):
            lang, start = lines[n][3:].strip(), n
            end = next((m for m in range(n + 1, len(lines)) if lines[m].startswith("```")), len(lines))
            if lang in SHELL_LANGS:
                yield start + 2, "\n".join(lines[start + 1:end])
            n = end + 1
        else:
            n += 1


# The forms section 9 and the card's "Known false positives" name, with the
# decision they document (True = allowed).
DOCUMENTED = [
    ("grep -rn 'aptly publish' docs", True, "section 9: readers may mention aptly and publish"),
    ("ls /srv/aptly/public", True, "section 9: readers"),
    ("cat docs/ENGINEERING-PROCESS.md | grep -n 'aptly publish'", True, "section 9: readers"),
    ("git log --oneline --grep 'aptly publish'", True, "section 9: git log is a reader"),
    ("echo \"B DONE: aptly publish is blocked\" >> ~/AGENTS-LOG.md", True, "section 9: echo"),
    ("python3 scripts/taskctl.py create --actor C \"infra: aptly publish via snapshots\"", True,
     "section 9: project scripts such as taskctl.py"),
    ("aptly -architectures=amd64 snapshot list", True, "section 9: write -architectures=amd64"),
    ("aptly -architectures amd64 snapshot list", False, "section 9 / card: space-separated value"),
    ("git commit -q -m \"$(cat <<'EOF'\ndocs: aptly publish notes\n\nEOF\n)\"", True,
     "section 9: commit messages in the heredoc form"),
    ("timeout 60 aptly repo list", False, "section 9: no timeout around aptly"),
    ("printf 'repo list' | xargs aptly", False, "section 9: no xargs around aptly"),
    ("bash -c 'aptly repo list'", False, "section 9: no bash -c around aptly"),
    ("A=aptly; $A repo list", False, "section 9 / card: no variable holding aptly"),
    ("python3 - <<'EOF'\nimport subprocess\nsubprocess.run(['aptly', 'repo', 'list'])\nEOF", False,
     "section 9 / card: Python heredoc that mentions aptly and starts processes"),
    ("apt-get source aptly", False, "card: apt-get with aptly"),
    ("ssh target2 'aptly repo list'", False, "card: ssh with aptly"),
    ("cat > /tmp/s.sh <<'EOF'\naptly repo list\nEOF\nsh /tmp/s.sh", False,
     "card: script written and run in the same call"),
    ("gh api repos/x/y/issues/$n --jq '.title' ; echo publish", False,
     "card: variable in a runner plus a listed word"),
    ("aptly publish list", False, "section 6 Aptly freeze: no direct aptly publish, list included"),
    ("aptly publish show resolute", False, "section 6 Aptly freeze: show included"),
    ("python3 scripts/taskctl.py transition --actor B UNITY-20260927-058 PUBLISHED", True,
     "section 6 Aptly freeze: taskctl.py's internal call is the exception"),
]


def hook(path, command):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run([sys.executable, path], input=payload, capture_output=True, text=True).returncode


def main():
    path = sys.argv[1]
    bad = 0
    print("## fenced shell blocks in the docs (documented workflows: expected to pass)")
    for doc in DOCS:
        text = (ROOT / doc).read_text()
        for line, block in shell_blocks(text):
            if not block.strip():
                continue
            rc = hook(path, block)
            mark = "ok  " if rc == 0 else "DENY"
            if rc:
                bad += 1
            first = block.strip().splitlines()[0][:90]
            print(f"{mark} {doc}:{line}  {first}")
    print("\n## forms documented in section 6/9 and the card")
    for command, allowed, source in DOCUMENTED:
        rc = hook(path, command)
        ok = (rc == 0) == allowed
        if not ok:
            bad += 1
        print(f"{'ok  ' if ok else 'FAIL'} expect {'allow' if allowed else 'deny '} rc={rc}  {source}")
    print(f"\nmismatches: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
