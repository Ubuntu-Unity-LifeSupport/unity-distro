#!/usr/bin/env python3
"""Wire .claude/hooks/command_guard.py into every Claude Code session of this user
(UNITY-20260928-012) and keep the permissions block next to it (permission
model phase 3).

Project settings are read only by sessions rooted in the project, so the
guard is registered in the user settings as well, with one handler that is
byte-identical to the project's (Claude Code runs an identical handler once).
The handler names the guard in the shared base checkout by absolute path and
turns every outcome except the guard's own exit 0 into exit 2: a missing
interpreter or file, a crash, a hang (inner timeout below the hook timeout)
and stdout (which Claude Code would parse as a JSON decision) cannot let a
call through. Design: docs/research/UNITY-20260928-012-guard-wiring/.

The permissions block (PERMISSIONS below) is a deny belt and an ask layer:
deny rules hold in every permission mode; ask rules make the built-in Edit and
Write tools prompt May for the trusted files (TRUSTED_FILES, TRUSTED_DIRS,
TRUSTED_GLOBS) and make a few shell forms of external or privileged writes
prompt him. The guard imports the trusted set from this file and refuses shell
writes into those files ("use Edit"). This installer never writes the live
user settings: `--propose` writes ~/.claude/settings.json.proposed and prints
the diff, and the live file is written with the Write tool, which asks.
Design: docs/research/permission-model-2026-10-09/phase3-permissions-block.md

  --check     read-only; exit 1 and say why when the wiring or the block is not in place
  --diff      print the change the proposal would make to the user settings
  --propose   write ~/.claude/settings.json.proposed (0600) and print the diff
  --apply     write a temporary settings file (tests); refuses the live user file
  --remove-permissions   with --propose/--apply/--diff: the proposal without the block
"""

import argparse
import difflib
import fnmatch
import glob
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

BASE = Path("/home/claude/unity-distro")
HOME = os.path.expanduser("~")
USER_SETTINGS = Path(HOME) / ".claude" / "settings.json"
PROPOSED_SUFFIX = ".proposed"
GUARD_RELPATH = ".claude/hooks/command_guard.py"
INSTALLER_RELPATH = "scripts/install_command_guard.py"
MATCHER = "Bash|Monitor"
HOOK_TIMEOUT = 30
INNER_TIMEOUT = 20
BACKUP_SUFFIX = ".bak-UNITY-20260928-012"
# Harmless probes for the end-to-end check: the guard denies the first two
# (pattern-based process matching; a shell write into a trusted file) and
# allows the third.
PROBE_DENIED = "pgrep -f unity-guard-probe-zzz"
PROBE_TRUSTED_WRITE = f"echo probe >> {HOME}/.claude/settings.json"
PROBE_ALLOWED = "true"
MANAGED_SETTINGS = Path("/etc/claude-code/managed-settings.json")

# ---- the trusted set (permission model phase 3) --------------------------------
# Files whose change alters what the sessions may do or who they are. The
# Edit/Write tools ask May (PERMISSIONS["ask"]); the guard refuses shell
# writes into them. Task worktrees under ~/work hold copies of the repository
# files and are ordinary work; only the base checkout is listed.
TRUSTED_FILES = tuple(str(p) for p in (
    USER_SETTINGS, USER_SETTINGS.with_name(USER_SETTINGS.name + ".local.json").with_name("settings.local.json"),
    USER_SETTINGS.with_name(USER_SETTINGS.name + PROPOSED_SUFFIX),
    USER_SETTINGS.with_name(USER_SETTINGS.name + BACKUP_SUFFIX),
    Path(HOME) / ".bashrc", Path(HOME) / ".profile", Path(HOME) / ".bash_profile", Path(HOME) / ".bash_aliases",
    Path(HOME) / ".gitconfig", Path(HOME) / ".ssh" / "authorized_keys", Path(HOME) / ".aptly.conf",
    BASE / "docs" / "ENGINEERING-PROCESS.md",
    BASE / "scripts" / "publish_aptly.py", BASE / "scripts" / "approval_record.py", BASE / "scripts" / "taskctl.py",
    BASE / "scripts" / "safe_git.py", BASE / "scripts" / "install_command_guard.py",
    BASE / "scripts" / "create_release_gate.py", BASE / "scripts" / "signer_client.py",
    BASE / "scripts" / "gpg_standin.py",
))
TRUSTED_DIRS = tuple(str(p) for p in (
    Path(HOME) / ".claude" / "plugins", Path(HOME) / ".claude" / "skills", Path(HOME) / ".claude" / "agents",
    Path(HOME) / ".claude" / "commands", Path(HOME) / ".claude" / "shell-snapshots",
    Path(HOME) / ".config" / "gh", Path(HOME) / ".gnupg", Path(HOME) / ".config" / "aptly-signer",
    BASE / ".claude", BASE / "signer",
))
TRUSTED_GLOBS = (str(Path(HOME) / ".ssh" / "id_*"),)
# sudoers is May's own change: the Edit/Write tools are denied, and the guard
# refuses every shell write (rule 3).
SUDOERS_PATHS = ("/etc/sudoers", "/etc/sudoers.d")


def _rule_path(path):
    return "//" + path.lstrip("/")


def _edit_write(pattern):
    return [f"Edit({pattern})", f"Write({pattern})"]


def permissions_block():
    deny = [
        "Bash(aptly publish)", "Bash(aptly publish *)",
        "Bash(aptly task)", "Bash(aptly task *)",
        "Bash(aptly api)", "Bash(aptly api *)",
        "Bash(git push --force)", "Bash(git push --force *)", "Bash(git push -f)", "Bash(git push -f *)",
        "Bash(xwd)", "Bash(xwd *)",
        *_edit_write(_rule_path("/etc/sudoers")), *_edit_write(_rule_path("/etc/sudoers.d/**")),
        f"Read({_rule_path(HOME + '/.gnupg/private-keys-v1.d/**')})",
    ]
    ask = []
    for path in TRUSTED_FILES:
        ask += _edit_write(_rule_path(path))
    for path in TRUSTED_DIRS:
        ask += _edit_write(_rule_path(path + "/**"))
    for pattern in TRUSTED_GLOBS:
        ask += _edit_write(_rule_path(pattern))
    ask += [
        # external writes (write subcommands only; reads stay unasked)
        "Bash(gh issue create *)", "Bash(gh issue comment *)", "Bash(gh issue close *)", "Bash(gh issue edit *)",
        "Bash(gh issue reopen *)", "Bash(gh issue transfer *)",
        "Bash(gh pr create *)", "Bash(gh pr comment *)", "Bash(gh pr merge *)", "Bash(gh pr close *)",
        "Bash(gh pr edit *)", "Bash(gh pr review *)", "Bash(gh pr ready *)",
        "Bash(gh release create *)", "Bash(gh release edit *)", "Bash(gh release delete *)", "Bash(gh release upload *)",
        "Bash(gh repo create *)", "Bash(gh repo edit *)", "Bash(gh repo delete *)", "Bash(gh repo rename *)",
        "Bash(gh repo fork *)", "Bash(gh repo sync *)", "Bash(gh repo archive *)",
        "Bash(gh api -X *)", "Bash(gh api --method *)", "Bash(gh api -F *)", "Bash(gh api -f *)",
        "Bash(gh api --field *)", "Bash(gh api --raw-field *)", "Bash(gh api --input *)",
        "Bash(curl -X *)", "Bash(curl --request *)", "Bash(curl -d *)", "Bash(curl --data *)",
        "Bash(curl --data-binary *)", "Bash(curl --data-raw *)", "Bash(curl -F *)", "Bash(curl --form *)",
        "Bash(curl -T *)", "Bash(curl --upload-file *)",
        "Bash(wget --post-data *)", "Bash(wget --post-file *)",
        "Bash(dput *)", "Bash(debsign *)", "Bash(bzr push *)",
        # privileged changes of trust state (visudo and sudoers writes are the guard's denials)
        "Bash(sudo usermod *)", "Bash(sudo useradd *)", "Bash(sudo passwd *)", "Bash(sudo chpasswd)", "Bash(sudo chpasswd *)",
        "Bash(gpg --gen-key)", "Bash(gpg --gen-key *)", "Bash(gpg --full-generate-key)", "Bash(gpg --full-generate-key *)",
        "Bash(gpg --quick-generate-key *)", "Bash(gpg --delete-secret-keys *)", "Bash(gpg --delete-secret-and-public-key *)",
        "Bash(gpg --export-secret-keys)", "Bash(gpg --export-secret-keys *)", "Bash(gpg --import)", "Bash(gpg --import *)",
    ]
    return {"deny": deny, "ask": ask}


PERMISSIONS = permissions_block()
_RULE_FORM = re.compile(r"^(Bash\([^*]+( \*)?\)|(Edit|Write|Read)\(//[^ ]+\))$")


def rule_form_problems():
    """Every Bash rule is an exact command or a prefix ending in ' *'; every path rule is absolute."""
    return [f"rule not in the documented form: {rule}" for rule in PERMISSIONS["deny"] + PERMISSIONS["ask"]
            if not _RULE_FORM.match(rule)]


# ---- the hook handler (UNITY-20260928-012) ---------------------------------------

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
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("hooks is not an object")
    groups = hooks.get("PreToolUse", [])
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


def proposal(data: dict, base: Path, remove_permissions: bool = False) -> dict:
    """The intended settings: the handler and, unless removed, the permissions block."""
    data = installed(data, base)
    if remove_permissions:
        data.pop("permissions", None)
    else:
        data["permissions"] = json.loads(json.dumps(PERMISSIONS))
    return data


def matches_bash(matcher) -> bool:
    """Claude Code matchers: empty or "*" match every tool, otherwise a regex."""
    if not matcher or matcher == "*":
        return True
    try:
        return re.fullmatch(str(matcher), "Bash") is not None
    except re.error:
        return True


def settings_problems(data: dict, base: Path, label: str, expect_block: bool = True) -> list:
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
            elif matches_bash(group.get("matcher")):
                problems.append(f"{label}: another PreToolUse hook also matches Bash: {entry!r}")
    if not found:
        problems.append(f"{label}: no command_guard handler")
    elif len(found) > 1:
        problems.append(f"{label}: {len(found)} command_guard handlers, expected one")
    elif found[0] != (MATCHER, handler(base)):
        problems.append(f"{label}: the command_guard handler differs from the expected one")
    permissions = data.get("permissions")
    if expect_block:
        if permissions != PERMISSIONS:
            problems.append(f"{label}: the permissions block is missing or differs from the installer's")
    if isinstance(permissions, dict):
        if permissions.get("allow"):
            problems.append(f"{label}: permissions.allow is not empty (inert under bypassPermissions, misleading)")
        for key in ("defaultMode", "disableBypassPermissionsMode", "disableAutoMode"):
            if key in permissions:
                problems.append(f"{label}: permissions.{key} is present (May's decision, not the installer's)")
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
    if git(base, "diff", "--quiet", "HEAD", "--", GUARD_RELPATH, ".claude/settings.json", INSTALLER_RELPATH).returncode != 0:
        problems.append(f"base: {GUARD_RELPATH}, .claude/settings.json or {INSTALLER_RELPATH} has uncommitted changes")
    behind = git(base, "rev-list", "--count", "HEAD..origin/main")
    if behind.returncode == 0 and behind.stdout.strip() != "0":
        notes.append(f"base: main is {behind.stdout.strip()} commit(s) behind origin/main as of the last fetch")
    return problems, notes


def environment_notes(settings: Path) -> tuple[list, list]:
    """Files that would silently change what the block means: a local settings
    file (fails), managed settings, allowedTools and user-site customisations (reported)."""
    problems, notes = [], []
    local = settings.with_name("settings.local.json")
    if local.exists():
        problems.append(f"{local} exists: the project settings of every session rooted at {HOME}; remove it or fold it in")
    if MANAGED_SETTINGS.exists():
        notes.append(f"{MANAGED_SETTINGS} exists and overrides everything here")
    claude_json = Path(HOME) / ".claude.json"
    try:
        allowed = [p for p, v in (json.loads(claude_json.read_text(encoding="utf-8")).get("projects") or {}).items()
                   if isinstance(v, dict) and v.get("allowedTools")]
    except (OSError, ValueError, AttributeError):
        allowed = []
    if allowed:
        notes.append(f"{claude_json} lists allowedTools for {', '.join(allowed)} (cannot defeat ask or deny)")
    customisations = glob.glob(os.path.join(HOME, ".local", "lib", "python3*", "site-packages", "usercustomize.py")) + \
        glob.glob(os.path.join(HOME, ".local", "lib", "python3*", "site-packages", "*.pth"))
    if customisations:
        notes.append("user-site customisations would run inside a non -I python: " + ", ".join(sorted(customisations)))
    return problems, notes


def run_handler(command: str, shell_command: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": HOME,
                          "tool_input": {"command": shell_command}})
    return subprocess.run(["/bin/sh", "-c", command], input=payload, capture_output=True, text=True,
                          timeout=HOOK_TIMEOUT + 5)


def live_problems(base: Path) -> list:
    command = handler(base)["command"]
    problems = []
    denied = run_handler(command, PROBE_DENIED)
    if denied.returncode != 2 or "Pattern-based process matching" not in denied.stderr:
        problems.append(f"handler: the deny probe gave rc {denied.returncode}: {denied.stderr.strip()!r}")
    trusted = run_handler(command, PROBE_TRUSTED_WRITE)
    if trusted.returncode != 2 or "trusted file" not in trusted.stderr:
        problems.append(f"handler: the trusted-write probe gave rc {trusted.returncode}: {trusted.stderr.strip()!r}")
    allowed = run_handler(command, PROBE_ALLOWED)
    if allowed.returncode != 0:
        problems.append(f"handler: the allow probe gave rc {allowed.returncode}: {allowed.stderr.strip()!r}")
    if denied.stdout or trusted.stdout or allowed.stdout:
        problems.append("handler: wrote to stdout")
    return problems


def check(settings: Path, base: Path) -> int:
    problems, notes = rule_form_problems(), []
    for path, label in ((settings, "user settings"), (base / ".claude/settings.json", "project settings")):
        try:
            problems += settings_problems(load(path), base, f"{label} {path}")
        except (OSError, ValueError) as error:
            problems.append(f"{label} {path}: {error}")
    more, notes = base_problems(base)
    problems += more
    env_problems, env_notes = environment_notes(settings)
    problems += env_problems
    notes += env_notes
    if not more:
        problems += live_problems(base)
    for line in problems + notes:
        print(line)
    print("command_guard wiring: " + ("NOT OK" if problems else "OK"))
    return 1 if problems else 0


def is_live_settings(path: Path) -> bool:
    try:
        return os.path.realpath(path) == os.path.realpath(USER_SETTINGS)
    except OSError:
        return False


def write_atomic(path: Path, text: str, mode: int | None = None):
    if is_live_settings(path):
        raise PermissionError(f"{path} is the live user settings; write it with the Write tool from the proposal")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        elif path.exists():
            os.chmod(tmp, path.stat().st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--diff", action="store_true")
    mode.add_argument("--propose", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--remove-permissions", action="store_true", help="propose/apply/diff without the permissions block")
    parser.add_argument("--settings", type=Path, default=USER_SETTINGS)
    parser.add_argument("--base", type=Path, default=BASE)
    args = parser.parse_args()
    if args.check:
        return check(args.settings, args.base)
    if args.settings.is_symlink():
        print(f"{args.settings} is a symlink; nothing written", file=sys.stderr)
        return 1
    try:
        current = load(args.settings)
        new = proposal(current, args.base, args.remove_permissions)
    except (OSError, ValueError) as error:
        print(f"{args.settings}: {error}; nothing written", file=sys.stderr)
        return 1
    old_text = args.settings.read_text(encoding="utf-8") if args.settings.exists() else ""
    new_text = dump(new)
    diff = "".join(difflib.unified_diff(old_text.splitlines(True), new_text.splitlines(True),
                                        str(args.settings), str(args.settings) + " (proposed)"))
    if args.diff:
        sys.stdout.write(diff)
        return 0
    if args.propose:
        proposed = args.settings.with_name(args.settings.name + PROPOSED_SUFFIX)
        try:
            write_atomic(proposed, new_text, mode=0o600)
        except (OSError, PermissionError) as error:
            print(f"{proposed}: {error}; nothing written", file=sys.stderr)
            return 1
        sys.stdout.write(diff or f"{args.settings}: already equal to the proposal\n")
        print(f"proposal written: {proposed} (write it over {args.settings} with the Write tool; the Write prompt is May's GO)")
        return 0
    # --apply: temporary settings only (tests); the live user file is refused in write_atomic
    if is_live_settings(args.settings):
        print(f"{args.settings} is the live user settings: use --propose, then write it with the Write tool", file=sys.stderr)
        return 1
    if old_text == new_text:
        print(f"{args.settings}: already up to date")
        return 0
    backup = args.settings.with_name(args.settings.name + BACKUP_SUFFIX)
    if old_text and not backup.exists():  # keep the first, pre-guard state
        write_atomic(backup, old_text)
    write_atomic(args.settings, new_text)
    print(f"{args.settings}: command_guard handler and permissions block installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
