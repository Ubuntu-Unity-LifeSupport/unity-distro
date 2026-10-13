"""Feed each phase R command to the guard as a hook payload, WITHOUT a session
id (so the rehearsal allowance can never match a marker and nothing is logged),
and print its verdict. Nothing is executed."""
import json
import subprocess
import sys

GUARD = "/home/claude/unity-distro/.claude/hooks/command_guard.py"
for tag, cmd in json.load(open(sys.argv[1])):
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(["/usr/bin/python3", "-I", GUARD], input=payload, capture_output=True, text=True)
    print(f"{tag}: {'ALLOW' if r.returncode == 0 else 'DENY' if r.returncode == 2 else r.returncode} {r.stderr.strip()}")
