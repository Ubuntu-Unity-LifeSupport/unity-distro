#!/usr/bin/env python3
"""Wire .claude/hooks/command_guard.py into every Claude Code session of this user (UNITY-20260928-012).

Project settings are read only by sessions rooted in the project, so the
guard is registered in the user settings as well, with one handler that is
byte-identical to the project's (Claude Code runs an identical handler once).
The handler names the guard in the shared base checkout by absolute path and
turns every outcome except the guard's own exit 0 into exit 2: a missing
interpreter or file, a crash, a hang (inner timeout below the hook timeout)
and stdout (which Claude Code would parse as a JSON decision) cannot let a
call through. Design: docs/research/UNITY-20260928-012-guard-wiring/.

  --check   read-only; exit 1 and say why when the wiring is not in place
  --diff    print the change --apply would make to the user settings
  --apply   write it (other keys kept, backup beside the file)
"""

import argparse
import difflib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

BASE = Path("/home/claude/unity-distro")
USER_SETTINGS = Path.home() / ".claude" / "settings.json"
GUARD_RELPATH = ".claude/hooks/command_guard.py"
MATCHER = "Bash|Monitor"
HOOK_TIMEOUT = 30
INNER_TIMEOUT = 20
BACKUP_SUFFIX = ".bak-UNITY-20260928-012"
# Harmless probes for the end-to-end check: the guard denies the first
# (pattern-based process matching) and allows the second.
PROBE_DENIED = "pgrep -f unity-guard-probe-zzz"
PROBE_ALLOWED = "true"


def handler_command(guard: Path) -> str:
    return (f"/usr/bin/timeout -s KILL {INNER_TIMEOUT} /usr/bin/python3 -I {guard} >/dev/null"
            ' || { rc=$?; [ "$rc" -eq 2 ] || echo "command_guard did not decide (rc=$rc);'
            ' tool call blocked." >&2; exit 2; }')


def handler(base: Path) -> dict:
    return {"type": "command", "command": handler_command(base / GUARD_RELPATH), "timeout": HOOK_TIMEOUT}


def is_guard_handler(entry) -> bool:
    return isinstance(entry, dict) and "command_guard.py" in str(entry.get("command", ""))


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def dump(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def pre_tool_use(data: dict) -> list:
    groups = data.get("hooks", {}).get("PreToolUse", [])
    if not isinstance(groups, list):
        raise ValueError("hooks.PreToolUse is not a list")
    return groups


def installed(data: dict, base: Path) -> dict:
    """Settings with every guard handler replaced by the one current handler."""
    data = json.loads(json.dumps(data))
    hooks = data.setdefault("hooks", {})
    groups = []
    for group in pre_tool_use(data):
        if isinstance(group, dict) and isinstance(group.get("hooks"), list):
            kept = [h for h in group["hooks"] if not is_guard_handler(h)]
            if not kept:
                continue
            group = dict(group, hooks=kept)
        groups.append(group)
    groups.append({"matcher": MATCHER, "hooks": [handler(base)]})
    hooks["PreToolUse"] = groups
    return data


def settings_problems(data: dict, base: Path, label: str) -> list:
    problems = []
    if data.get("disableAllHooks"):
        problems.append(f"{label}: disableAllHooks is set")
    found = []
    for group in pre_tool_use(data):
        if not isinstance(group, dict):
            continue
        for entry in group.get("hooks", []) if isinstance(group.get("hooks"), list) else []:
            if is_guard_handler(entry):
                found.append((group.get("matcher"), entry))
            elif "Bash" in str(group.get("matcher", "")) or not group.get("matcher"):
                problems.append(f"{label}: another PreToolUse hook also matches Bash: {entry!r}")
    if not found:
        problems.append(f"{label}: no command_guard handler")
    elif len(found) > 1:
        problems.append(f"{label}: {len(found)} command_guard handlers, expected one")
    elif found[0] != (MATCHER, handler(base)):
        problems.append(f"{label}: the command_guard handler differs from the expected one")
    return problems


def git(base: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(base), *args], capture_output=True, text=True)


def base_problems(base: Path) -> tuple[list, list]:
    problems, notes = [], []
    if not (base / GUARD_RELPATH).is_file():
        return [f"base: {base / GUARD_RELPATH} does not exist"], notes
    head = git(base, "symbolic-ref", "-q", "HEAD")
    if head.stdout.strip() != "refs/heads/main":
        problems.append(f"base: {base} is not on main (HEAD: {head.stdout.strip() or 'detached'})")
    if git(base, "diff", "--quiet", "HEAD", "--", GUARD_RELPATH, ".claude/settings.json").returncode != 0:
        problems.append(f"base: {GUARD_RELPATH} or .claude/settings.json has uncommitted changes")
    behind = git(base, "rev-list", "--count", "HEAD..origin/main")
    if behind.returncode == 0 and behind.stdout.strip() != "0":
        notes.append(f"base: main is {behind.stdout.strip()} commit(s) behind origin/main as of the last fetch")
    return problems, notes


def run_handler(command: str, shell_command: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                          "tool_input": {"command": shell_command}})
    return subprocess.run(["/bin/sh", "-c", command], input=payload, capture_output=True, text=True,
                          timeout=HOOK_TIMEOUT + 5)


def live_problems(base: Path) -> list:
    command = handler(base)["command"]
    problems = []
    denied = run_handler(command, PROBE_DENIED)
    if denied.returncode != 2 or "Pattern-based process matching" not in denied.stderr:
        problems.append(f"handler: the deny probe gave rc {denied.returncode}: {denied.stderr.strip()!r}")
    allowed = run_handler(command, PROBE_ALLOWED)
    if allowed.returncode != 0:
        problems.append(f"handler: the allow probe gave rc {allowed.returncode}: {allowed.stderr.strip()!r}")
    if denied.stdout or allowed.stdout:
        problems.append("handler: wrote to stdout")
    return problems


def check(settings: Path, base: Path) -> int:
    problems, notes = [], []
    for path, label in ((settings, "user settings"), (base / ".claude/settings.json", "project settings")):
        try:
            problems += settings_problems(load(path), base, f"{label} {path}")
        except (OSError, ValueError) as error:
            problems.append(f"{label} {path}: {error}")
    more, notes = base_problems(base)
    problems += more
    if not more:
        problems += live_problems(base)
    for line in problems + notes:
        print(line)
    print("command_guard wiring: " + ("NOT OK" if problems else "OK"))
    return 1 if problems else 0


def write_atomic(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        if path.exists():
            os.chmod(tmp, path.stat().st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--diff", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--settings", type=Path, default=USER_SETTINGS)
    parser.add_argument("--base", type=Path, default=BASE)
    args = parser.parse_args()
    if args.check:
        return check(args.settings, args.base)
    try:
        current = load(args.settings)
        new = installed(current, args.base)
    except (OSError, ValueError) as error:
        print(f"{args.settings}: {error}; nothing written", file=sys.stderr)
        return 1
    old_text = args.settings.read_text(encoding="utf-8") if args.settings.exists() else ""
    new_text = dump(new)
    if args.diff:
        sys.stdout.writelines(difflib.unified_diff(old_text.splitlines(True), new_text.splitlines(True),
                                                   str(args.settings), str(args.settings) + " (new)"))
        return 0
    if old_text == new_text:
        print(f"{args.settings}: already up to date")
        return 0
    if old_text:
        write_atomic(args.settings.with_name(args.settings.name + BACKUP_SUFFIX), old_text)
    write_atomic(args.settings, new_text)
    print(f"{args.settings}: command_guard handler installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
