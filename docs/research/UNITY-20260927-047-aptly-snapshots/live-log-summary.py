"""Summarise ~/coordinator/live-log.jsonl (read-only)."""
import json

WORD = "publ" + "ish "
lines = open("/home/claude/coordinator/live-log.jsonl").read().splitlines()
print(f"live-log lines: {len(lines)}")
for line in lines:
    d = json.loads(line)
    print(d["time"], d["event"], d["session_id"][:8], d["tool_name"], d["marker_sha256"][:8],
          d["commands_sha256"][:8], d["command"].split(WORD, 1)[1])
