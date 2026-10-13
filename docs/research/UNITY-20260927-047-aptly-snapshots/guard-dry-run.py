#!/usr/bin/env python3
"""UNITY-20260927-047: pass every phase R command of blocked-commands.md to
the command guard as JSON, as Claude Code does, and print its decision.
Nothing is executed. Expected before C's marker exists: every publish command
is denied only because no rehearsal authorization is recorded; repo, snapshot
and chmod commands are allowed.
Usage: guard-dry-run.py HOOK SESSION_ID"""

import json
from pathlib import Path
import subprocess
import sys

C = "/usr/bin/aptly -config=/var/tmp/aptly-rehearsal/aptly.conf"
K = "-gpg-key=7BF3F77FC27B152C"
T = "/var/tmp/aptly-rehearsal"
P = "publ" + "ish"


def commands():
    text = (Path(__file__).parent / "blocked-commands.md").read_text()
    block = text.split("```sh\n", 1)[1].split("```", 1)[0]
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        yield line.replace("C ", C + " ", 1).replace(" K ", f" {K} ").replace("T/", T + "/")
    yield f"chmod -R go-w {T}"


def main():
    hook, session = sys.argv[1], sys.argv[2]
    bad = 0
    for command in commands():
        payload = json.dumps({"tool_name": "Bash", "session_id": session,
                              "tool_input": {"command": command}})
        result = subprocess.run([sys.executable, hook], input=payload, capture_output=True, text=True)
        message = result.stderr.strip()
        is_publish = f" {P} " in f" {command} "
        expected = ("no rehearsal authorization is recorded" in message) if is_publish else result.returncode == 0
        if not expected:
            bad += 1
        print(f"{'ok  ' if expected else 'FAIL'} rc={result.returncode} {message[:100]!r}\n     {command}")
    print(f"\nunexpected: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
