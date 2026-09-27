#!/usr/bin/env python3
"""Maintain the current A/B/C registry separately from append-only history."""

import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path

ROOT = Path.home() / "coordinator"
REGISTRY = ROOT / "AGENT-REGISTRY.json"
HISTORY = Path.home() / "AGENTS-HISTORY.md"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    reg = commands.add_parser("register")
    reg.add_argument("role", choices=["A", "B", "C"])
    reg.add_argument("--name", required=True)
    reg.add_argument("--session-id", default="UNKNOWN")
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    REGISTRY.touch(exist_ok=True)
    with REGISTRY.with_suffix(".json.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            data = json.loads(REGISTRY.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as exc:
            parser.error(f"registry JSON is invalid: {exc}")
        if not isinstance(data, dict): parser.error("registry must be a JSON object")
        if args.command == "list":
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return 0
        current = data.get(args.role)
        if isinstance(current, dict) and current.get("name") == args.name and current.get("session_id") == args.session_id:
            print(f"{args.role} already registered")
            return 0
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
        data[args.role] = {"name": args.name, "session_id": args.session_id, "registered_at": stamp}
        temp = REGISTRY.with_suffix(".json.tmp")
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(REGISTRY)
        line = f"{stamp} {args.role} name={args.name} session={args.session_id}\n"
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a", encoding="utf-8") as history:
            fcntl.flock(history, fcntl.LOCK_EX)
            history.write(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
