#!/usr/bin/env python3
"""UNITY-20260929-008 post-merge proof, run in a NEW session. Feeds hook payloads
to the installed guard (the handler's own file in the base checkout), exactly
as Claude Code does, and prints each decision. NOTHING is executed: the
commands are only JSON on the guard's stdin. With no live marker every listed
string must be denied (before L0 by the 0664 config, after it by "no live
authorization"); near-misses, Monitor and
background calls must be denied with their own reasons; the live log must not
appear. Usage: live-proof.py SESSION_ID"""

import hashlib
import json
import os
import subprocess
import sys

GUARD = "/home/claude/unity-distro/.claude/hooks/command_guard.py"
LIST = "/home/claude/unity-distro/.claude/hooks/live-commands.json"
LOG = "/home/claude/coordinator/live-log.jsonl"
MARKER = "/home/claude/coordinator/live-authorization.json"
session = sys.argv[1]


def decide(command, tool="Bash", background=False):
    tool_input = {"command": command}
    if background:
        tool_input["run_in_background"] = True
    payload = json.dumps({"session_id": session, "hook_event_name": "PreToolUse",
                          "tool_name": tool, "tool_input": tool_input})
    r = subprocess.run(["/usr/bin/python3", "-I", GUARD], input=payload, capture_output=True, text=True)
    return r.returncode, r.stderr.strip()


with open(LIST, "rb") as f:
    data = f.read()
commands = json.loads(data)["commands"]
print(f"list sha256 {hashlib.sha256(data).hexdigest()} ({len(commands)} commands)")
print(f"live marker present: {os.path.lexists(MARKER)}; live log present: {os.path.lexists(LOG)}")
bad = 0
for i, c in enumerate(commands, 1):
    rc, err = decide(c)
    # Before -047's L0, ~/.aptly.conf is 0664 and stops the chain before the
    # marker check; after L0 the reason is "no live authorization". Both deny.
    ok = rc == 2 and ("no live authorization" in err or "live aptly config must be owned" in err)
    bad += not ok
    print(f"L{i} listed, no marker: rc={rc} {'OK' if ok else 'UNEXPECTED'} | {err}")
for label, kw, command in [("near-miss (extra space)", {}, commands[2] + " "),
                           ("near-miss (extra arg)", {}, commands[6] + " x"),
                           ("Monitor tool", {"tool": "Monitor"}, commands[6]),
                           ("background", {"background": True}, commands[6])]:
    rc, err = decide(command, **kw)
    ok = rc == 2
    bad += not ok
    print(f"{label}: rc={rc} {'OK' if ok else 'UNEXPECTED'} | {err}")
print(f"live log present after: {os.path.lexists(LOG)}")
print("RESULT:", "all denied as expected" if bad == 0 and not os.path.lexists(LOG) else f"{bad} unexpected")
