#!/usr/bin/env python3
"""Replay real Bash commands through the old and the new guard (UNITY-20260927-058).

Reads the tool_use inputs of Bash and Monitor calls from Claude Code session
transcripts (JSONL) and prints every command whose decision differs between
two versions of command_guard.py, plus totals. The commands are only parsed,
never executed. Usage: corpus.py OLD_HOOK NEW_HOOK TRANSCRIPT...
"""

import importlib.util
import json
import sys


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def commands(paths):
    for path in paths:
        with open(path, errors="replace") as f:
            for line in f:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = (record.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for item in content:
                    if (isinstance(item, dict) and item.get("type") == "tool_use"
                            and item.get("name") in ("Bash", "Monitor")
                            and isinstance(item.get("input", {}).get("command"), str)):
                        yield item["input"]["command"]


def main():
    old, new = load(sys.argv[1], "old_guard"), load(sys.argv[2], "new_guard")
    seen, total, changed = set(), 0, {"newly_denied": [], "newly_allowed": []}
    for command in commands(sys.argv[3:]):
        if command in seen:
            continue
        seen.add(command)
        total += 1
        a, b = old.inspect(command), new.inspect(command)
        if bool(a) != bool(b):
            changed["newly_denied" if b else "newly_allowed"].append((command, a or b))
    print(f"unique commands: {total}")
    for kind, items in changed.items():
        print(f"\n== {kind}: {len(items)}")
        for command, message in items:
            one = command if len(command) < 300 else command[:300] + " ..."
            print(f"-- [{message}]\n{one}")


if __name__ == "__main__":
    main()
