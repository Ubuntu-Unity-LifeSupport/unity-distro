#!/usr/bin/env python3
"""Block a small set of repeatedly dangerous shell command forms."""

import json
import re
import sys


def deny(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def inspect(command: str) -> str | None:
    checks = [
        (
            r"\bgit\s+add\s+(?:--all|-A|\.|docs/?)(?=\s|$)",
            "Stage explicit file paths; broad staging is blocked.",
        ),
        (
            r"\bgit\s+push\b[^\n;&|]*(?:--force(?:-with-lease)?|(?<!\S)-f)(?:\s|$)",
            "Force-push is blocked by project policy.",
        ),
        (
            r"(?:^|(?:&&|\|\||[;&|])\s*)(?:sudo\s+)?aptly\s+publish\b",
            "Publish through scripts/publish_aptly.py with a passing release-gate record.",
        ),
        (
            r"(?:^|(?:&&|\|\||[;&|])\s*)(?:sudo\s+)?xwd(?:\s|$)",
            "xwd is blocked; use the assigned desktop screenshot procedure.",
        ),
        (
            r"\b(?:pkill|pgrep)\b[^\n;&|]*(?:^|\s)(?:-[^\s]*f|--full)(?:\s|$)",
            "Pattern-based process matching is blocked; identify the exact PID.",
        ),
    ]
    for pattern, message in checks:
        if re.search(pattern, command):
            return message

    # Recursive removal is permitted only with literal paths or a braced
    # variable that uses the shell's required-value guard (${NAME:?}).
    for match in re.finditer(
        r"\brm\s+(?:-[A-Za-z]*[rf][A-Za-z]*\s+|-r\s+-f\s+|-f\s+-r\s+)"
        r"([^\n;&|]+)",
        command,
    ):
        paths = match.group(1)
        if re.search(r"(?<!\\)[*?]", paths):
            return "rm -rf with a glob is blocked; name the exact paths."
        for variable in re.finditer(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", paths):
            guarded = re.match(
                r"\$\{" + re.escape(variable.group(1)) + r":\?[^}]*\}",
                paths[variable.start() :],
            )
            if not guarded:
                return (
                    "rm -rf with an unguarded variable is blocked; use an exact "
                    "path or ${NAME:?}/... after confirming the variable."
                )
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return deny("Command guard could not read the hook input; tool call blocked.")

    tool_input = payload.get("tool_input", {})
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return deny("Command guard found no Bash command; tool call blocked.")

    message = inspect(command)
    if message:
        return deny(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
