#!/usr/bin/env python3
"""UNITY-20260927-057 reproduction: the 047 phase R command, as data only,
through the current command guard. Nothing is executed. Usage: repro.py HOOK"""

import json
import subprocess
import sys

CONFIG = "/var/tmp/aptly-rehearsal/aptly.conf"
COMMANDS = [
    "aptly -config=" + CONFIG + " " + "publ" + "ish list",
    "aptly -config=" + CONFIG + " " + "publ" + "ish repo -distribution=resolute -architectures=amd64 -batch unity-resolute",
]

for command in COMMANDS:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    result = subprocess.run([sys.executable, sys.argv[1]], input=payload, capture_output=True, text=True)
    print(f"rc={result.returncode} {result.stderr.strip()[:90]!r} :: {command}")
