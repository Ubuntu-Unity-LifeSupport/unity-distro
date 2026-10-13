#!/usr/bin/env python3
"""Alerts for the coordinator: raised by automation, acknowledged by C or May.

An alert is something no one asked for that someone must act on - a watcher
found a new upload, or a watcher itself keeps failing. The alert file
(ALERTS_FILE, default ~/coordinator/ALERTS.md) is append-only and written
under flock, one line per event:

    2026-10-03 09:00Z RAISE xorg-server:2:21.1.22-1ubuntu1.4@Proposed xorg-watch: <text>
    2026-10-03 11:12Z ACK xorg-server:2:21.1.22-1ubuntu1.4@Proposed by C: <note>

A key is raised at most once, so a watcher may raise on every run. An alert
is open from its RAISE until an ACK for its key. scripts/taskctl.py prints
every open alert on each run until it is acknowledged, so the coordinator
sees it at its next board operation. Acknowledging does not create a task:
only C or May allocates task IDs (taskctl create) and decides what the alert
means.

Usage:
  alerts.py raise --source NAME --key KEY --message TEXT
  alerts.py ack --actor C|May --key KEY [--note TEXT]
  alerts.py open
"""

import argparse
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import re
import sys

LINE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}Z (RAISE|ACK) (\S+) (.*)$")


def alerts_path():
    return Path(os.environ.get("ALERTS_FILE", str(Path.home() / "coordinator/ALERTS.md"))).expanduser()


def stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")


def one_line(text):
    return " ".join(text.split())


def parse(text):
    """Return (raised, acked): raised maps key -> its RAISE line, acked is a set."""
    raised, acked = {}, set()
    for line in text.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        kind, key = m.group(1), m.group(2)
        if kind == "RAISE":
            raised.setdefault(key, line)
        else:
            acked.add(key)
    return raised, acked


def open_alerts(path=None):
    """RAISE lines of the alerts not acknowledged yet, oldest first."""
    path = path or alerts_path()
    if not path.is_file():
        return []
    raised, acked = parse(path.read_text(encoding="utf-8"))
    return [line for key, line in raised.items() if key not in acked]


def main():
    parser = argparse.ArgumentParser(description="Raise, acknowledge and list coordinator alerts.")
    subs = parser.add_subparsers(dest="command", required=True)
    r = subs.add_parser("raise")
    r.add_argument("--source", required=True)
    r.add_argument("--key", required=True)
    r.add_argument("--message", required=True)
    a = subs.add_parser("ack")
    a.add_argument("--actor", choices=["C", "May"], required=True)
    a.add_argument("--key", required=True)
    a.add_argument("--note", default="")
    subs.add_parser("open")
    args = parser.parse_args()

    path = alerts_path()
    if args.command == "open":
        for line in open_alerts(path):
            print(line)
        return 0
    if not re.fullmatch(r"\S+", args.key):
        parser.error("a key has no whitespace")
    if args.command == "raise" and not one_line(args.message):
        parser.error("message must not be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        raised, acked = parse(stream.read())
        if args.command == "raise":
            if args.key in raised:
                print(f"already raised: {args.key}")
                return 0
            line = f"{stamp()} RAISE {args.key} {one_line(args.source)}: {one_line(args.message)}"
        else:
            if args.key not in raised:
                print(f"alerts: no alert with key {args.key}", file=sys.stderr)
                return 1
            if args.key in acked:
                print(f"already acknowledged: {args.key}")
                return 0
            line = f"{stamp()} ACK {args.key} by {args.actor}: {one_line(args.note) or '-'}"
        stream.seek(0, 2)
        stream.write(line + "\n")
        stream.flush()
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
