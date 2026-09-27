#!/usr/bin/env python3
"""A narrow Bash command-pattern safety net; not a shell security boundary."""

import json
import os
import re
import shlex
import sys


DENY_MESSAGES = {
    "stage": "Stage explicit file paths; broad staging is blocked.",
    "push": "Force pushes and force refspecs are blocked by project policy.",
    "publish": "Publish through scripts/publish_aptly.py with a passing release gate.",
    "xwd": "xwd is blocked; use the assigned desktop screenshot procedure.",
    "process": "Pattern-based process matching is blocked; identify the exact PID.",
    "remove": "Recursive forced removal with a glob or unguarded variable is blocked.",
}


def _command_tokens(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|\n")
    lexer.whitespace_split = True
    lexer.commenters = ""
    groups: list[list[str]] = [[]]
    try:
        for token in lexer:
            if token and all(char in ";&|\n" for char in token):
                groups.append([])
            else:
                groups[-1].append(token)
    except ValueError:
        # Malformed quoting is not safe to reason about.
        return [["<parse-error>"]]
    return [group for group in groups if group]


def _unwrap(tokens: list[str]) -> list[str]:
    """Skip harmless command prefixes and assignments before matching."""
    i = 0
    while i < len(tokens):
        base = os.path.basename(tokens[i])
        if base in {"command", "builtin", "exec"}:
            i += 1
            if i < len(tokens) and tokens[i] == "--": i += 1
        elif base == "sudo":
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                option = tokens[i]
                takes_value = option in {"-u", "--user", "-g", "--group", "-h", "--host", "-C", "--chdir", "-R", "--chroot", "-p", "--prompt", "-D"}
                i += 2 if takes_value and i + 1 < len(tokens) else 1
        elif base == "env":
            i += 1
            while i < len(tokens) and ("=" in tokens[i] or tokens[i].startswith("-")):
                i += 1
        elif "=" in tokens[i] and tokens[i].split("=", 1)[0].replace("_", "a").isalnum():
            i += 1
        else:
            break
    return tokens[i:]


def _is_option(token: str, short: str, long: str) -> bool:
    return token == long or token.startswith(long + "=") or (token.startswith("-") and not token.startswith("--") and any(char in token[1:] for char in short))


_GUARDED_PARAMETER = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*:\?[^}]*\}")
_VARIABLE_EXPANSION = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*|\$\{[^}]+\}")


def _rm_is_dangerous(tokens: list[str]) -> bool:
    if not tokens or os.path.basename(tokens[0]) != "rm":
        return False
    recursive = forced = False
    paths: list[str] = []
    options = True
    i = 1
    while i < len(tokens):
        token = tokens[i]
        if options and token == "--":
            options = False
        elif options and token.startswith("-"):
            recursive |= _is_option(token, "rR", "--recursive")
            forced |= _is_option(token, "f", "--force")
        else:
            options = False
            paths.append(token)
        i += 1
    if not (recursive and forced):
        return False
    for path in paths:
        without_guards = _GUARDED_PARAMETER.sub("", path)
        if any(c in without_guards for c in "*?["):
            return True
        if _VARIABLE_EXPANSION.search(without_guards):
            return True
    return False


def inspect(command: str) -> str | None:
    for raw in _command_tokens(command):
        tokens = _unwrap(raw)
        if not tokens:
            continue
        base = os.path.basename(tokens[0])
        if base == "<parse-error>":
            return "Command guard could not parse shell quoting; tool call blocked."
        args = tokens[1:]

        if base == "git":
            # Git global options (for example -C /repo) precede the subcommand.
            i = 0
            while i < len(args):
                arg = args[i]
                if arg in {"-C", "--git-dir", "--work-tree", "--namespace", "-c"}:
                    i += 2
                elif arg.startswith(("--git-dir=", "--work-tree=", "--namespace=", "-c")):
                    i += 1
                elif arg.startswith("-"):
                    i += 1
                else:
                    break
            sub = args[i] if i < len(args) else ""
            subargs = args[i + 1:]
            if sub == "add" and any(a in {"-A", "--all", ".", "docs", "docs/"} for a in subargs):
                return DENY_MESSAGES["stage"]
            if sub == "push":
                if any(_is_option(a, "f", "--force") or a.startswith("--force-with-lease") for a in subargs):
                    return DENY_MESSAGES["push"]
                # A leading '+' on a refspec is force even without --force.
                if any(a.startswith("+") for a in subargs):
                    return DENY_MESSAGES["push"]

        if base == "aptly" and args and args[0] == "publish":
            return DENY_MESSAGES["publish"]
        if base == "xwd":
            return DENY_MESSAGES["xwd"]
        if base in {"pkill", "pgrep"} and any(_is_option(a, "f", "--full") for a in args):
            return DENY_MESSAGES["process"]
        if _rm_is_dangerous(tokens):
            return DENY_MESSAGES["remove"]
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        print("Command guard could not read the hook input; tool call blocked.", file=sys.stderr)
        return 2
    tool_input = payload.get("tool_input", {})
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        print("Command guard found no Bash command; tool call blocked.", file=sys.stderr)
        return 2
    message = inspect(command)
    if message:
        print(message, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
