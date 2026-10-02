"""Feed each probe to the installed handler (never executes the probe itself)."""
import json
import subprocess
import sys

settings = json.load(open("/home/claude/.claude/settings.json"))
command = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
probes = json.load(open(sys.argv[1]))
for probe in probes:
    payload = json.dumps({"session_id": "probe-check", "hook_event_name": "PreToolUse", "tool_name": "Bash",
                          "tool_input": {"command": probe["command"]}})
    r = subprocess.run(["/bin/sh", "-c", command], input=payload, capture_output=True, text=True, timeout=40)
    got = "allow" if r.returncode == 0 else "deny" if r.returncode == 2 else f"rc{r.returncode}"
    print(f"{probe['id']}: expect {probe['expect']} got {got} {'OK' if got == probe['expect'] else 'MISMATCH'} | {r.stderr.strip()}")
