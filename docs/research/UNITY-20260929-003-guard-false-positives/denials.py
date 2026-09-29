"""Collect every Bash/Monitor command the command guard refused, from Claude
Code transcripts (read-only): the command text, the refusal reason, the
transcript. Writes JSON to argv[1]; prints counts by reason."""
import collections
import glob
import json
import sys

out = []
for path in sorted(glob.glob("/home/claude/.claude/projects/*/*.jsonl")):
    uses = {}
    for line in open(path, errors="replace"):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use" and part.get("name") in ("Bash", "Monitor"):
                cmd = (part.get("input") or {}).get("command")
                if isinstance(cmd, str):
                    uses[part.get("id")] = (part.get("name"), cmd)
            if part.get("type") == "tool_result":
                c = part.get("content")
                if isinstance(c, list):
                    c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                c = str(c)
                if "PreToolUse:" in c and "hook error" in c and part.get("tool_use_id") in uses:
                    reason = c.split("]: ", 1)[-1].strip()[:200]
                    tool, cmd = uses[part["tool_use_id"]]
                    out.append({"transcript": path.rsplit("/", 1)[1], "tool": tool, "reason": reason, "command": cmd})
json.dump(out, open(sys.argv[1], "w"), indent=1)
counts = collections.Counter(d["reason"][:90] for d in out)
print(f"{len(out)} refusals")
for reason, n in counts.most_common():
    print(f"{n:4} {reason}")
