#!/usr/bin/env python3
"""Append a fallback peer message or explicit read acknowledgement under flock."""

import argparse
from datetime import datetime, timezone
import fcntl
from pathlib import Path


def stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    send = subs.add_parser("append")
    send.add_argument("--recipient", choices=["A", "B"], required=True)
    send.add_argument("--sender", choices=["A", "B", "C", "May"], required=True)
    send.add_argument("--message", required=True)
    ack = subs.add_parser("ack")
    ack.add_argument("--reader", choices=["A", "B", "C"], required=True)
    ack.add_argument("--inbox-owner", choices=["A", "B"], required=True)
    ack.add_argument("--through", required=True, help="timestamp/heading of the last message handled")
    args = parser.parse_args()
    inbox_owner = args.recipient if args.command == "append" else args.inbox_owner
    path = Path.home() / f"PEER-INBOX-{inbox_owner}.md"
    if not path.is_file(): parser.error(f"inbox does not exist: {path}")
    if args.command == "append":
        body = "\n  ".join(line.strip() for line in args.message.splitlines())
        if not body: parser.error("message must not be empty")
        message = f"\n\n{stamp()} {args.sender} -> {args.recipient}: {body}"
    else:
        if args.reader not in {args.inbox_owner, "C"}:
            parser.error("only the inbox owner records its acknowledgement")
        message = f"\n\n{stamp()} ACK by {args.reader} through {args.through.replace(chr(10), ' ').replace(chr(13), ' ')}"
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        if args.command == "ack":
            stream.seek(0)
            if args.through not in stream.read(): parser.error("acknowledgement target is not present in this inbox")
        stream.seek(0, 2)
        stream.write(message + "\n")
        stream.flush()
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
