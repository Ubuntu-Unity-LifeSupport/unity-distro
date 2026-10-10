#!/usr/bin/env python3
"""A narrow Bash command-pattern safety net; not a shell security boundary.

The aptly rules (UNITY-20260927-058, docs/research/UNITY-20260927-058-command-guard)
do not try to follow aptly's flag grammar. When a command involves aptly, or
contains a shell expansion, the words publish, task and api anywhere deny it; a
literal aptly command must start with one of aptly's other commands; any other
mention of aptly passes only in a command made of plain readers.
"""

import codecs
import fnmatch
import json
import os
import re
import shlex
import stat
import sys


DENY_MESSAGES = {
    "stage": "Stage explicit file paths; broad staging is blocked.",
    "push": "Force pushes and force refspecs are blocked by project policy.",
    "publish": "Publish through scripts/publish_aptly.py with a passing release gate.",
    "aptly_words": ("aptly publish/task/api is blocked in any form (publish through "
                    "scripts/publish_aptly.py; a command with a shell expansion must not name them)."),
    "aptly_command": ("aptly must be called literally with one of: repo snapshot mirror package db "
                      "config serve version graph."),
    "aptly_mention": ("aptly may only be run directly, or named in a command made of plain readers "
                      "(grep, ls, cat, git log, ...)."),
    "aptly_copy": "Copying or linking the aptly binary is blocked.",
    "xwd": "xwd is blocked; use the assigned desktop screenshot procedure.",
    "process": "Pattern-based process matching is blocked; identify the exact PID.",
    "remove": "Recursive forced removal with a glob or unguarded variable is blocked.",
    "trusted": "trusted file {path}: edit it with the Edit tool, which asks May.",
    "sudoers": "sudoers is May's own change; the shell may not write under /etc/sudoers.",
}

SUBST = "__SUBST__"
QUOTED_GT = "\ue000"  # ">" inside quotes: text, not a redirection
HEREDOC = "__HEREDOC__"
MAX_DEPTH = 8


class ScanError(Exception):
    pass


class Body:
    def __init__(self, text, quoted):
        self.text, self.quoted = text, quoted


class Level:
    """One piece of shell text: the outer command, a substitution or a heredoc body.

    groups[n] is a command's tokens and seps[n] the separator after it. A body
    level is checked by the aptly rules only. sink_safe: this level's output
    only reaches a command that runs nothing (a commit message, the terminal).
    """
    def __init__(self, groups, seps, bodies=(), subs=(), expansion=False, body=False,
                 sink_safe=True, consumer=None, blob=False, forced=False):
        self.groups, self.seps = groups, seps
        self.bodies, self.subs = list(bodies), list(subs)
        self.expansion, self.body, self.sink_safe = expansion, body, sink_safe
        self.consumer = consumer  # the command whose argument this substitution is
        self.blob = blob  # text in another language: its words count, it is no command
        # UNITY-20260929-018: a body written where git or a later command may run it;
        # its words are checked even when the call has no runner.
        self.forced = forced


_BRACE = re.compile(r"\{[^\s{}'\"]*(,|\.\.)[^\s{}'\"]*\}")


class _Scanner:
    """Quote-aware pass over shell text.

    Produces the text with every $(...) and `...` replaced by SUBST and every
    heredoc operator by HEREDOC, the raw texts of those substitutions, the
    heredoc bodies, and whether any expansion occurs outside single quotes.
    $'...' is decoded; backslash-newline is removed; comments are dropped.
    """

    def __init__(self, text):
        self.t = text
        self.i = 0
        self.subs = []
        self.bodies = []
        self.pending = []
        self.expansion = False

    def run(self):
        out = self._plain(end=None, record=True)
        if self.i < len(self.t):
            raise ScanError("unbalanced )")
        return out

    def _peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else ""

    def _single(self):
        end = self.t.find("'", self.i + 1)
        if end < 0:
            raise ScanError("unterminated '")
        s = self.t[self.i:end + 1]
        self.i = end + 1
        return s

    def _ansi_c(self):
        j = self.i + 2
        raw = []
        while j < len(self.t) and self.t[j] != "'":
            if self.t[j] == "\\" and j + 1 < len(self.t):
                raw.append(self.t[j:j + 2])
                j += 2
            else:
                raw.append(self.t[j])
                j += 1
        if j >= len(self.t):
            raise ScanError("unterminated $'")
        self.i = j + 1
        try:
            decoded = codecs.decode("".join(raw), "unicode_escape")
        except (UnicodeDecodeError, ValueError):
            self.expansion = True
            decoded = "".join(raw)
        return "'" + decoded.replace("'", "'\"'\"'") + "'"

    def _substitution(self, end):
        start = self.i
        self._plain(end=end, record=False)
        self.subs.append(self.t[start:self.i - 1])
        self.expansion = True
        return SUBST

    def _dollar(self, out):
        nxt = self._peek(1)
        if nxt == "(":
            self.i += 2
            out.append(self._substitution(")"))
            return True
        if nxt == "'":
            out.append(self._ansi_c().replace(">", QUOTED_GT))
            return True
        if nxt and (nxt.isalnum() or nxt in "_{@*#?!$-"):
            self.expansion = True
        return False

    def _double(self):
        out = ['"']
        self.i += 1
        while True:
            c = self._peek()
            if not c:
                raise ScanError('unterminated "')
            if c == "\\":
                if self._peek(1) == "\n":
                    self.i += 2
                    continue
                out.append(self.t[self.i:self.i + 2])
                self.i += 2
            elif c == '"':
                out.append('"')
                self.i += 1
                return "".join(out)
            elif c == "`":
                self.i += 1
                out.append(self._substitution("`"))
            elif c == "$" and self._dollar(out):
                continue
            else:
                out.append(c)
                self.i += 1

    def _heredoc(self, out):
        self.i += 2
        strip = False
        if self._peek() == "-":
            strip = True
            self.i += 1
        while self._peek() in (" ", "\t"):
            self.i += 1
        word, quoted = [], False
        while True:
            c = self._peek()
            if not c or c.isspace() or c in ";&|()<>":
                break
            if c == "'":
                word.append(self._single()[1:-1])
                quoted = True
            elif c == '"':
                end = self.t.find('"', self.i + 1)
                if end < 0:
                    raise ScanError("unterminated heredoc delimiter")
                word.append(self.t[self.i + 1:end])
                self.i = end + 1
                quoted = True
            elif c == "\\":
                word.append(self._peek(1))
                self.i += 2
                quoted = True
            elif c in "$`":
                raise ScanError("heredoc delimiter with expansion")
            else:
                word.append(c)
                self.i += 1
        delimiter = "".join(word)
        if not delimiter:
            raise ScanError("heredoc without delimiter")
        self.pending.append((delimiter, strip, quoted))
        out.append(f" {HEREDOC} ")

    def _read_bodies(self, record):
        # self.i is just after the newline that ends the operator's line.
        for delimiter, strip, quoted in self.pending:
            lines = []
            while self.i < len(self.t):
                nl = self.t.find("\n", self.i)
                line = self.t[self.i:nl if nl >= 0 else len(self.t)]
                self.i = nl + 1 if nl >= 0 else len(self.t)
                if (line.lstrip("\t") if strip else line) == delimiter:
                    break
                lines.append(line.lstrip("\t") if strip else line)
            if record:
                self.bodies.append(Body("\n".join(lines), quoted))
        self.pending = []

    def _plain(self, end, record):
        out = []
        depth = 0
        while self.i < len(self.t):
            c = self._peek()
            if c == "\\":
                if self._peek(1) == "\n":
                    self.i += 2
                else:
                    out.append(self.t[self.i:self.i + 2])
                    self.i += 2
            elif c == "'":
                out.append(self._single().replace(">", QUOTED_GT))
            elif c == '"':
                out.append(self._double().replace(">", QUOTED_GT))
            elif c == "`":
                if end == "`":
                    self.i += 1
                    return "".join(out)
                self.i += 1
                out.append(self._substitution("`"))
            elif c == "$" and self._dollar(out):
                continue
            elif c == "<" and self._peek(1) == "<":
                if self._peek(2) == "<":
                    out.append("<<<")
                    self.i += 3
                else:
                    self._heredoc(out)
            elif c == "#" and (not out or out[-1][-1:].isspace() or out[-1][-1:] in ";&|()"):
                while self.i < len(self.t) and self.t[self.i] != "\n":
                    self.i += 1
            elif c == "\n":
                out.append("\n")
                self.i += 1
                if self.pending:
                    self._read_bodies(record)
            elif c == "(":
                depth += 1
                out.append(c)
                self.i += 1
            elif c == ")":
                if end == ")" and depth == 0:
                    self.i += 1
                    return "".join(out)
                depth -= 1
                out.append(c)
                self.i += 1
            else:
                if c in "*?[" or (c == "{" and _BRACE.match(self.t, self.i)):
                    self.expansion = True
                out.append(c)
                self.i += 1
        if end is not None:
            raise ScanError(f"unterminated {end}")
        if self.pending:
            self.pending = []
        return "".join(out)


_BARE_GT = re.compile(r"^\d*>$")


def _lex(text: str) -> tuple[list[list[str]], list[str]]:
    """Command groups and the separator after each (";", "|", "&&", newline, ...)."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|\n()")
    lexer.whitespace_split = True
    lexer.whitespace = " \t\r"
    lexer.commenters = ""
    raw = list(lexer)
    merged: list[str] = []
    n = 0
    while n < len(raw):
        token = raw[n]
        # "2>&1", ">&2": shlex splits the "&" off as a separator.
        if token == "&" and merged and merged[-1].endswith(">") and n + 1 < len(raw) \
                and (raw[n + 1].isdigit() or raw[n + 1] == "-"):
            merged[-1] += "&" + raw[n + 1]
            n += 2
            continue
        # "&>file", "&>>file": a redirection, not a background "&".
        if token == "&" and n + 1 < len(raw) and raw[n + 1].startswith(">"):
            merged.append("&" + raw[n + 1])
            n += 2
            continue
        # ">|file": the clobbering redirection, not a pipe (permission model phase 3).
        if token == "|" and merged and _BARE_GT.match(merged[-1]):
            merged[-1] += "|"
            n += 1
            continue
        merged.append(token)
        n += 1
    groups: list[list[str]] = [[]]
    seps: list[str] = [""]
    for token in merged:
        if token and all(char in ";&|\n()" for char in token):
            if groups[-1]:
                seps[-1] = token
                groups.append([])
                seps.append("")
            elif len(groups) > 1 and "|" in token and "|" not in seps[-2]:
                seps[-2] += token
        else:
            groups[-1].append(token)
    if not groups[-1]:
        groups.pop()
        seps.pop()
    return groups, seps


def _pipes(sep: str) -> bool:
    """The command's output goes to the next command (| or |&, also across a newline)."""
    return sep.startswith("|") and not sep.startswith("||")


def _collect(text: str, depth: int, levels: list, body: bool = False, sink_safe: bool = True,
             consumer: list | None = None) -> None:
    """Scan text and its substitutions recursively into levels (bodies unresolved)."""
    if depth > MAX_DEPTH:
        raise ScanError("nesting too deep")
    scanner = _Scanner(text)
    outer = scanner.run()
    try:
        groups, seps = _lex(outer)
    except ValueError as error:
        raise ScanError(str(error))
    level = Level(groups, seps, scanner.bodies, scanner.subs, scanner.expansion, body, sink_safe,
                  consumer=consumer)
    levels.append(level)
    # The n-th substitution belongs to the command holding the n-th SUBST marker.
    consumers = [(group, sep) for group, sep in zip(groups, seps)
                 for token in group for _ in range(token.count(SUBST))]
    for n, sub in enumerate(scanner.subs):
        group, sep = consumers[n] if n < len(consumers) else ([], "|")
        safe = sink_safe and _is_sink(group, sep)
        _collect(sub, depth + 1, levels, body, safe, group or None)


def _body_substitutions(text: str) -> list[str]:
    """$(...) and `...` in an unquoted heredoc body: they run although the body is text."""
    found, i = [], 0
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
        elif c == "$" and text[i + 1:i + 2] == "(":
            scanner = _Scanner(text)
            scanner.i = i + 2
            scanner._plain(end=")", record=False)
            found.append(text[i + 2:scanner.i - 1])
            i = scanner.i
        elif c == "`":
            end = text.find("`", i + 1)
            if end < 0:
                raise ScanError("unterminated ` in heredoc")
            found.append(text[i + 1:end])
            i = end + 1
        else:
            i += 1
    return found


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


# --- aptly (UNITY-20260927-058) ----------------------------------------------

APTLY_COMMANDS = {"repo", "snapshot", "mirror", "package", "db", "config", "serve", "version", "graph"}
# "aptly" as a command name; not publish_aptly.py, .aptly.conf, aptly.conf, aptly047,
# /srv/aptly/<dir> or a hyphenated name such as 047-aptly-snapshots.
_APTLY_TEXT = re.compile(r"(?<![_.-])aptly(?![_./0-9-])")
_DENIED_WORD = re.compile(r"(?<![A-Za-z0-9_.-])(publish|task|api)(?![A-Za-z0-9_.-])")
_SHELL_WORDS = {"{", "!", "time", "if", "then", "elif", "else", "while", "until", "do"}
_COPIERS = {"cp", "ln", "install", "mv", "rsync", "dd", "tee"}
_READERS = {"grep", "egrep", "fgrep", "ls", "stat", "file", "sha256sum", "sha1sum", "md5sum",
            "readlink", "realpath", "dpkg-query", "which", "type", "echo", "head", "tail", "wc",
            "cut", "cat", "test", "[", "sort", "uniq", "printf", "apt-cache", "git", "command",
            "date", "pwd", "basename", "dirname", "hostname", "uname", "id", "whoami", "true",
            "false", "seq", "tr", "pgrep", "pidof", "ps", "du", "df", "nproc", "cd", "mkdir",
            "touch", "set", "sleep", "diff", "cmp", "comm", "jq", "od", "xxd", "strings", "nl",
            "column", "sha512sum", "b2sum", "cksum", "curl", "wget", "tac", "rev", "fold", "fmt",
            "expand", "paste", "join", "tty", "lsblk", "free", "uptime", "tee",
            "printenv", "locale", "getent", "dpkg-deb", "apt-mark", "zcat", "gunzip", "gzip",
            "xz", "unxz", "bzip2", "sed",
            # file operations: they run nothing (a copy of the binary is rule C)
            "cp", "mv", "rm", "rmdir", "mkdir", "chmod", "chown", "ln", "install",
            # shell words that run nothing by themselves
            "for", "in", "done", "fi", "esac", "}", "break", "continue", "return", "exit",
            "case", "local", "export", "unset", "shift", "wait", "read", "declare", ":"}
_SED_SCRIPT = re.compile(r"^([0-9$]+(,[0-9$]+)?|/[^/]*/(,/[^/]*/)?)?[pd=]$")
# Permission model phase 1 (UNITY-20260929-003 RC4): one substitution script,
# any one-character delimiter that is not alphanumeric, backslash, newline or
# whitespace; flags g, I, i, p and a number only (no e, w, m).
_SED_SUBST = re.compile(r"^s(?P<d>[^\w\\\n\s])(?:\\.|(?!(?P=d))[^\\\n])*(?P=d)(?:\\.|(?!(?P=d))[^\\\n])*(?P=d)[gIip0-9]*$")
_SED_OPTIONS = ("-n", "-E", "-r", "-i", "-s", "-z", "-u", "--quiet")
# Non-shell programs that read a heredoc body as their own language.
_INTERPRETERS = re.compile(r"^(python[0-9.]*|perl|ruby|node|php|lua|tclsh|cat|tee)$")
# Project scripts that never hand their arguments to a shell or to aptly.
_PROJECT_READERS = re.compile(r"(^|/)scripts/(taskctl|agent_registry|append_record|safe_git|"
                              r"create_release_gate|version_safety|peer_inbox)\.py$")
# git subcommands that run commands or strings given to them, or set config for later runs.
_GIT_RUNS = {"bisect", "submodule", "filter-branch", "filter-repo", "difftool", "mergetool", "config",
             "daemon", "instaweb", "web--browse", "send-email", "credential", "hook", "run",
             "rebase", "archive", "worktree", "clone", "alias"}
_GIT_DENIED_OPTIONS = ("--config-env", "--exec-path", "-O", "--open-files-in-pager",
                       "--output", "--ext-diff", "--textconv", "-x", "--exec", "--upload-pack",
                       "--receive-pack")
_GIT_SAFE_CONFIG = {"user.name", "user.email", "commit.gpgsign", "color.ui", "core.quotepath"}
# A heredoc body in another language counts only if it can start a process.
_STARTS_PROCESS = re.compile(r"\bsubprocess\b|\bsystem\s*\(|\bpopen\b|\bexec[lv]?p?e?\s*\(|\bspawn|\bpty\b|"
                             r"__import__|\beval\s*\(|\bimportlib\b|\bctypes\b|\bgetattr\s*\(|"
                             r"\bfork\s*\(|\bexecSync\b|\bchild_process\b|\bqx\b|"
                             r"\bopen\s*\(\s*['\"]\s*\||\bos\.exec", re.I)
# The longer operators first (phase 3: ">|" is not ">" to "|"; phase 2: "2>&1" is a
# fd duplication, not a write to "&1").
_REDIRECT = re.compile(r"^(\d*|&)(>&|>\||>>|>)(.*)$")


class AptlyCall:
    """A group whose command word is aptly; the point where UNITY-20260927-057 decides."""
    def __init__(self, args, bare, command, configs, env, literal):
        self.args, self.bare, self.command = args, bare, command
        self.configs, self.env, self.literal = configs, env, literal


def _which(name: str) -> str | None:
    for directory in os.environ.get("PATH", os.defpath).split(os.pathsep):
        path = os.path.join(directory or ".", name)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _same_as_aptly(token: str, aptly: str | None, command: bool = True) -> bool:
    """The token names the aptly binary itself: by path, glob or (as a command
    word) PATH lookup, compared by inode."""
    if not aptly or not token or token.startswith("-"):
        return False
    path = os.path.expanduser(token)
    if any(c in path for c in "*?["):
        import glob
        candidates = glob.glob(path)[:64]
    elif "/" in path or not command:
        candidates = [path]
    else:
        which = _which(token)
        candidates = [which] if which else []
    for candidate in candidates:
        try:
            if os.path.samefile(candidate, aptly):
                return True
        except OSError:
            continue
    return False


def _is_aptly(token: str, aptly: str | None) -> bool:
    """An occurrence: the name aptly in the text, a path named aptly that is not a
    directory (/srv/aptly is data), or the binary itself under any name."""
    if os.path.basename(token.rstrip("/")) == "aptly" and os.path.isdir(os.path.expanduser(token)):
        return False
    return bool(_APTLY_TEXT.search(token)) or _same_as_aptly(token, aptly)


def _command_index(group: list[str]) -> int:
    """Index of the command word: past env/sudo/command prefixes, assignments and shell words."""
    i = 0
    while i < len(group):
        rest = _unwrap(group[i:])
        i = len(group) - len(rest)
        if i < len(group) and group[i] in _SHELL_WORDS:
            i += 1
            continue
        break
    return i


def _aptly_call(group: list[str], index: int, expansion: bool) -> AptlyCall:
    args = group[index + 1:]
    bare, configs = [], []
    skip = False
    for token in args:
        if skip:
            configs.append(token)
            skip = False
            continue
        if token.startswith("-"):
            name, eq, value = token.lstrip("-").partition("=")
            if name == "config" and len(token) - len(token.lstrip("-")) <= 2:
                if eq:
                    configs.append(value)
                else:
                    skip = True
            continue
        bare.append(token)
    env = [t for t in group[:index] if "=" in t]
    return AptlyCall(args, bare, bare[0] if bare else "", configs, env,
                     literal=not expansion and os.path.basename(group[index]) == "aptly")


def _aptly_denial(call: AptlyCall) -> str | None:
    """Rule E. UNITY-20260927-057 adds its rehearsal allowance here, for publish only."""
    if any(_DENIED_WORD.search(token) for token in call.args):
        return DENY_MESSAGES["aptly_words"]
    if call.command not in APTLY_COMMANDS:
        return DENY_MESSAGES["aptly_command"]
    return None


def _redirect_targets(group: list[str]) -> list[str] | None:
    """Output redirection targets (fd duplications excluded); None if unparsable."""
    targets = []
    for n, token in enumerate(group):
        match = _REDIRECT.match(token)
        if match:
            op, target = match.group(2), match.group(3)
            if not target and n + 1 < len(group):
                target = group[n + 1]
            if op == ">&" and (target.isdigit() or target == "-"):
                continue
            targets.append(target)
        elif ">" in token:
            return None
    return targets


def _is_reader(group: list[str], aptly: str | None) -> bool:
    """A command that runs nothing else: a plain reader, a pure assignment."""
    while group and group[0] in _SHELL_WORDS:
        group = group[1:]
    if not group:
        return True
    if all("=" in t and t.split("=", 1)[0].replace("_", "a").isalnum() for t in group):
        return True
    targets = _redirect_targets(group)
    if targets is None:
        return False
    if all(_REDIRECT.match(t) or t.startswith(("&>", "<")) for t in group):
        return True
    word, args = group[0], group[1:]
    if re.fullmatch(r"python3?", word) and args and _PROJECT_READERS.search(args[0]):
        return True
    if _PROJECT_READERS.search(word):
        return True
    if word not in _READERS:
        return False
    if any(t != "/dev/null" for t in targets) and any(_same_as_aptly(a, aptly, False) for a in args):
        return False  # a copy of the binary under another name
    if word == "command":
        return bool(args) and args[0] in ("-v", "-V")
    if word == "sort":
        return not any(a.startswith(("--output", "--compress-program"))
                       or (a.startswith("-") and not a.startswith("--") and "o" in a[1:]) for a in args)
    if word == "uniq":
        return len([a for a in args if not a.startswith("-")]) <= 1
    if word == "printf":
        return "-v" not in args
    if word == "sed":
        # Printing scripts (sed -n 5,9p file) and, since phase 1 (RC4), one
        # substitution script without the aptly word or publish/task/api (a
        # sed -i write is not followed by _exposed); s///e, e and w run or
        # write. Operands are existing files that are not the aptly binary.
        scripts = [a for a in args if _SED_SCRIPT.match(a) or _SED_SUBST.match(a)]
        if any(_SED_SUBST.match(a) and ("aptly" in a or _DENIED_WORD.search(a)) for a in scripts):
            return False  # the written text must not carry the words at all
        if len([a for a in scripts if _SED_SUBST.match(a)]) > 1:
            return False
        return all(a in _SED_OPTIONS or a in scripts
                   or (not a.startswith("-") and not any(c.isspace() for c in a) and "/" in a
                       and os.path.isfile(os.path.expanduser(a)) and not _same_as_aptly(a, aptly, False))
                   for a in args)
    if word == "apt-cache":
        return not any(a.startswith(("-o", "-c", "--option", "--config-file")) for a in args)
    if word == "git":
        if any(a.startswith(_GIT_DENIED_OPTIONS) for a in args):
            return False
        i = 0
        while i < len(args) and args[i].startswith("-"):
            if args[i] == "-c" or args[i].startswith("-c"):
                setting = args[i][2:] or (args[i + 1] if i + 1 < len(args) else "")
                if setting.split("=", 1)[0].lower() not in _GIT_SAFE_CONFIG:
                    return False
                i += 1 if args[i][2:] else 2
                continue
            i += 2 if args[i] in ("-C", "--git-dir", "--work-tree") else 1
        return i < len(args) and args[i] not in _GIT_RUNS
    return True


def _is_sink(group: list[str], sep: str) -> bool:
    """A substitution's output only becomes a git commit/tag message."""
    if _pipes(sep) or not group or group[0] != "git":
        return False
    return _is_reader(group, None) and any(t in ("commit", "tag") for t in group[1:3])


def word_of(group: list[str]) -> str:
    index = _command_index(group)
    return os.path.basename(group[index]) if index < len(group) else ""


def _heredoc_owners(level: Level) -> list[tuple[list[str], str]]:
    return [(group, sep) for group, sep in zip(level.groups, level.seps)
            for token in group if token == HEREDOC]


_GIT_FILES = {"config", ".gitconfig", ".gitattributes", ".gitmodules"}


def _git_component(path: str) -> bool:
    return ".git" in path.replace("\\", "/").split("/")


def _owner_output_groups(level: Level, owner: list[str]) -> list[list[str]]:
    """The groups whose redirections receive the owner's output: the owner, an
    earlier `exec` redirection, and the closing done/fi/esac/} after it."""
    index = next((n for n, g in enumerate(level.groups) if g is owner), None)
    if index is None:
        return list(level.groups)
    before = [g for g in level.groups[:index] if g and os.path.basename(g[0]) == "exec"]
    after = [g for g in level.groups[index + 1:] if g and g[0] in ("done", "fi", "esac", "}")]
    return before + [owner] + after


def _text_blockers(level: Level, levels: list[Level], owner: list[str] | None = None) -> tuple[bool, bool]:
    """UNITY-20260929-018: (text_ok, forced) for a heredoc body of this level.

    A body is text only when nothing in the call can run it: no subshell, brace
    group, function or process substitution around it, no pipe into a command
    that runs something, no runner with an expansion or glob, and no file
    written that a runner or git (hooks, config, attributes) may run.
    """
    runners = [g for lv in levels if not lv.blob for g in lv.groups if not _is_reader(g, None)]
    compound = any("(" in s or ")" in s for s in level.seps) or \
        any(g and g[0] in ("{", "}") for g in level.groups)
    piped = any(_pipes(level.seps[n]) and n + 1 < len(level.groups)
                and not _is_reader(level.groups[n + 1], None) for n in range(len(level.groups)))
    expands = any(SUBST in t or any(c in t for c in "$*?[") for g in runners for t in g)
    targets, unknown = [], False
    for g in (_owner_output_groups(level, owner) if owner is not None else level.groups):
        found = _redirect_targets(g)
        if found is None:
            unknown = True
        else:
            targets += [t for t in found if t != "/dev/null"]
    tokens = [t for lv in levels for g in lv.groups for t in g]
    git_path = any(_git_component(t) or os.path.basename(t) in _GIT_FILES for t in targets) or \
        any("hooksPath" in t for t in tokens) or \
        any(word_of(g) in ("cd", "ln") and any(_git_component(t) for t in g[_command_index(g) + 1:])
            for lv in levels for g in lv.groups)
    writes = bool(targets) or unknown
    forced = writes and (bool(runners) or git_path)
    return not (compound or piped or expands or forced), forced


_GIT_COMMIT_STDIN = {"-F-", "--file=-"}
_GIT_COMMIT_TEXT_FLAGS = {"-q", "--quiet", "-s", "--signoff", "--no-verify", "--amend", "--allow-empty"}
_GIT_COMMIT_TEXT_PREFIXES = ("--author=", "--date=")


def _git_commit_stdin_message(group: list[str]) -> bool:
    """Permission model phase 1 (UNITY-20260929-003 RC1b): `git commit` reading
    its message from stdin (-F -, -F-, --file=-, --file -) with only operands
    git never runs: a few flags, --author=/--date= values, pathspecs after --.
    Global git options are walked as _is_reader does; an unsafe -c, an editor
    or template option, -a or anything else keeps the body SCRIPT."""
    tokens = [t for t in group if t != HEREDOC and not _REDIRECT.match(t)]
    if not tokens or os.path.basename(tokens[0]) != "git":
        return False
    args = tokens[1:]
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-c" or args[i].startswith("-c"):
            setting = args[i][2:] or (args[i + 1] if i + 1 < len(args) else "")
            if setting.split("=", 1)[0].lower() not in _GIT_SAFE_CONFIG:
                return False
            i += 1 if args[i][2:] else 2
            continue
        if args[i] in ("-C", "--git-dir", "--work-tree"):
            i += 2
        elif args[i].startswith(("--git-dir=", "--work-tree=")):
            i += 1
        else:
            return False
    if i >= len(args) or args[i] != "commit":
        return False
    rest = args[i + 1:]
    stdin = False
    j = 0
    while j < len(rest):
        token = rest[j]
        if token == "--":
            break  # pathspecs: read, never run
        if token in ("-F", "--file") and j + 1 < len(rest) and rest[j + 1] == "-":
            stdin = True
            j += 2
            continue
        if token in _GIT_COMMIT_STDIN:
            stdin = True
        elif token in _GIT_COMMIT_TEXT_FLAGS or token.startswith(_GIT_COMMIT_TEXT_PREFIXES):
            pass
        else:
            return False
        j += 1
    return stdin


def _classify_body(body: Body, group: list[str], sep: str, level: Level, other_tokens: list[str],
                   everything_reads: bool, text_ok: bool = True) -> str:
    """TEXT (never runs), BLOB (another language: one token) or SCRIPT (shell)."""
    index = _command_index(group)
    word = os.path.basename(group[index]) if index < len(group) else ""
    keyword = word in ("done", "fi", "esac", "}")
    if keyword and not everything_reads:
        return "SCRIPT"
    if text_ok and level.sink_safe and not _pipes(sep) and _git_commit_stdin_message(group):
        return "TEXT"  # RC1b: git only reads the message
    if text_ok and (keyword or _is_reader(group, None)) and level.sink_safe and not _pipes(sep):
        # An unquoted body's $(...) and `...` are collected separately; the rest is text.
        targets = _redirect_targets(group) or []
        operands = [t for t in group[index + 1:] if t != HEREDOC and not _REDIRECT.match(t)
                    and t not in targets]
        names = {os.path.basename(t) for t in targets if t != "/dev/null"}
        used_elsewhere = any(name in token for name in names for token in other_tokens)
        if not operands and not used_elsewhere:
            return "TEXT"
    if _INTERPRETERS.match(word) and not (word in ("cat", "tee") and _pipes(sep)):
        return "BLOB"
    return "SCRIPT"


def _levels(command: str, fallback: bool = False) -> list[Level]:
    """All levels of the command, heredoc bodies classified and added. With
    fallback (the whole-text floor failed to lex and the fallback decided), a
    SCRIPT body that fails to scan becomes a forced blob, so its words are
    checked without a runner (permission model phase 1, RC1)."""
    levels: list[Level] = []
    _collect(command, 0, levels)
    seen = 0
    while seen < len(levels):
        level = levels[seen]
        seen += 1
        owners = _heredoc_owners(level)
        for n, body in enumerate(level.bodies):
            group, sep = owners[n] if n < len(owners) else (["sh"], "")
            others = [t for lv in levels for g in lv.groups
                      if g is not group and not _is_reader(g, None) for t in g]
            everything = all(_is_reader(g, None) for lv in levels if not lv.blob for g in lv.groups)
            text_ok, forced = _text_blockers(level, levels, group)
            kind = _classify_body(body, group, sep, level, others, everything, text_ok)
            if not body.quoted:
                for sub in _body_substitutions(body.text):
                    _collect(sub, 1, levels, level.body)
            if kind == "BLOB":
                owner = word_of(group)
                if owner in ("cat", "tee") or forced or _STARTS_PROCESS.search(body.text) or \
                        (owner in ("perl", "ruby", "php") and "`" in body.text):
                    levels.append(Level([[body.text]], [""], body=True, blob=True, forced=forced))
            elif kind == "SCRIPT":
                part: list = []
                try:
                    _collect(body.text, 1, part, body=True)
                except ScanError:
                    part = [Level([[body.text]], [""], body=True, blob=True, forced=forced or fallback)]
                levels.extend(part)
        level.bodies = []
    return levels


def _exposed(levels: list[Level], runners: set) -> set:
    """Groups whose words can reach a command that runs something: the runner
    itself, a command piping into it, a substitution it consumes, an assignment
    it may expand, a file written for it."""
    exposed = set(runners)
    runner_tokens = [t for level in levels for g in level.groups if id(g) in runners for t in g]
    expands = any("$" in t or SUBST in t for t in runner_tokens)
    for level in levels:
        for group in level.groups:
            if expands and group and all("=" in t and t.split("=", 1)[0].replace("_", "a").isalnum()
                                         for t in group):
                exposed.add(id(group))
            targets = [t for t in (_redirect_targets(group) or []) if t != "/dev/null"]
            if any(os.path.basename(t) in rt for t in targets for rt in runner_tokens):
                exposed.add(id(group))
    changed = True
    while changed:
        changed = False
        for level in levels:
            if level.consumer is not None and id(level.consumer) in exposed:
                for group in level.groups:
                    if id(group) not in exposed:
                        exposed.add(id(group))
                        changed = True
            for n in range(len(level.groups) - 2, -1, -1):
                if _pipes(level.seps[n]) and id(level.groups[n + 1]) in exposed \
                        and id(level.groups[n]) not in exposed:
                    exposed.add(id(level.groups[n]))
                    changed = True
    return exposed


def _token_expands(token: str) -> bool:
    return SUBST in token or "$" in token or any(c in token for c in "*?[") or bool(_BRACE.search(token))


def _expands_where_it_runs(level, n, group, runners, runner_tokens, exposed) -> bool:
    """Permission model phase 2 (a): the group's expansion can build a command -
    the group runs something, or it is a reader whose output reaches a runner
    (a pipe into any non-reader, a file a runner names, a substitution an
    exposed command consumes)."""
    if not any(_token_expands(t) for t in group):
        return False
    if id(group) in runners:
        return True
    targets = [t for t in (_redirect_targets(group) or []) if t != "/dev/null"]
    if any(os.path.basename(t) in rt for t in targets for rt in runner_tokens):
        return True
    if level.consumer is not None and id(level.consumer) in exposed:
        return True
    m = n
    while m < len(level.groups) - 1 and _pipes(level.seps[m]):
        m += 1
        if id(level.groups[m]) in runners:
            return True
    return False


def _aptly_rules(levels: list[Level]) -> str | None:
    aptly = _which("aptly")
    commands = [level for level in levels if not level.blob]
    blobs = [token for level in levels if level.blob for group in level.groups for token in group]
    tokens = [t for level in commands for group in level.groups for t in group] + blobs
    expansion = any(level.expansion for level in levels)
    if not expansion and not any(_is_aptly(token, aptly) for token in tokens):
        return None
    # Literal aptly commands: rule E. Every other command that is not a reader runs something.
    runners, literal = set(), set()
    for level in commands:
        for group in level.groups:
            index = _command_index(group)
            if index < len(group) and _is_aptly(group[index], aptly):
                message = _aptly_denial(_aptly_call(group, index, expansion))
                if message:
                    return message
                literal.add(id(group))
                continue
            if any(_same_as_aptly(t, aptly, False) for t in group[index + 1:]) and \
                    group[index:index + 1] and os.path.basename(group[index]) in _COPIERS:
                return DENY_MESSAGES["aptly_copy"]
            if not _is_reader(group, aptly):
                runners.add(id(group))
    if not runners and not any(level.forced for level in levels):
        return None  # readers and literal aptly commands only: nothing else runs
    exposed = _exposed(commands, runners)
    runner_tokens = [t for level in commands for g in level.groups if id(g) in runners for t in g]
    reach = [t for level in commands for g in level.groups
             if id(g) in exposed and id(g) not in literal for t in g] + blobs
    # (a) the expansion counts where a command may be built from it, not anywhere in the level
    reach_expansion = bool(blobs) or any(level.expansion and id(g) in exposed and id(g) not in literal
                                         and _expands_where_it_runs(level, n, g, runners, runner_tokens, exposed)
                                         for level in commands for n, g in enumerate(level.groups))
    words = any(_DENIED_WORD.search(t) for t in reach)
    mentions = [t for t in reach if _is_aptly(t, aptly)]
    if words and (mentions or reach_expansion):
        return DENY_MESSAGES["aptly_words"]
    if mentions:
        return DENY_MESSAGES["aptly_mention"]
    return None


_GUARDED_PARAMETER = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*:\?[^}]*\}")
_VARIABLE_EXPANSION = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*|\$\{[^}]+\}")


def _is_option(token: str, short: str, long: str) -> bool:
    return token == long or token.startswith(long + "=") or (token.startswith("-") and not token.startswith("--") and any(char in token[1:] for char in short))


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


def _legacy_groups(command: str) -> list[list[str]]:
    """The tokenisation of the guard before UNITY-20260927-058 (newline is whitespace)."""
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


# --- aptly rehearsal allowance (UNITY-20260927-057) ----------------------------
#
# ENGINEERING-PROCESS section 6: during a freeze direct `aptly publish` is
# denied, except for the rehearsal phase of a task May authorized, on an
# isolated aptly state, through C's dated marker. The allowance admits one
# literal /usr/bin/aptly publish command whose configuration confines every
# place aptly writes to the rehearsal root. Design and review:
# docs/research/UNITY-20260927-057-rehearsal-allowance/.

REHEARSAL_ROOT = "/var/tmp/aptly-rehearsal"
REHEARSAL_COORDINATOR = "/home/claude/coordinator"
REHEARSAL_MARKER = REHEARSAL_COORDINATOR + "/rehearsal-authorization.json"
REHEARSAL_LOG = REHEARSAL_COORDINATOR + "/rehearsal-log.jsonl"
APTLY_BINARY = "/usr/bin/aptly"
LIVE_APTLY = "/srv/aptly"
MOUNTINFO = "/proc/self/mountinfo"
REHEARSAL_MAX_ENTRIES = 200000
REHEARSAL_MAX_FILE = 64 * 1024
REHEARSAL_MAX_WINDOW = 24 * 3600

# Only these characters, single spaces between words: no quoting, expansion,
# redirection, separator, newline or comment can occur.
_REHEARSAL_SHAPE = re.compile(r"^[A-Za-z0-9_./=:,+@-]+( [A-Za-z0-9_./=:,+@-]+)*$")
_UTC_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

# config key -> expected type ("path" is a string checked as a path)
_CONFIG_SCHEMA = {
    "rootDir": "path", "architectures": "strlist",
    "gpgDisableSign": bool, "gpgDisableVerify": bool,
    "dependencyFollowSuggests": bool, "dependencyFollowRecommends": bool,
    "dependencyFollowAllVariants": bool, "dependencyFollowSource": bool,
    "skipContentsPublishing": bool, "skipBz2Publishing": bool,
    "gpgProvider": str, "logLevel": str, "logFormat": str, "downloader": str,
    "downloadConcurrency": int, "databaseOpenAttempts": int,
    "FileSystemPublishEndpoints": "endpoints",
    "databaseBackend": "database", "packagePoolStorage": "pool",
}
_MARKER_KEYS = {"schema", "task_id", "root", "authorized_by", "recorded_by",
                "not_before", "not_after", "reference", "session_id"}


class RehearsalDenied(Exception):
    pass


def _deny(reason: str):
    raise RehearsalDenied(reason)


def _owned_private(st, what: str):
    if st.st_uid != os.getuid() or st.st_mode & 0o022:
        _deny(f"{what} must be owned by uid {os.getuid()} and not writable by group or others")


def _inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _real_inside(path: str, root: str) -> bool:
    """realpath of path (or of its nearest existing ancestor plus the rest) is inside root."""
    head, tail = path, []
    while not os.path.lexists(head):
        head, name = os.path.split(head)
        tail.insert(0, name)
        if not head or head == "/":
            break
    real = os.path.join(os.path.realpath(head), *tail) if tail else os.path.realpath(head)
    return _inside(os.path.normpath(real), root)


def _strict_json(path: str, what: str, private: bool = True):
    st = os.lstat(path)
    if not stat.S_ISREG(st.st_mode):
        _deny(f"{what} must be a regular file, not a link")
    if private:
        _owned_private(st, what)
    elif st.st_uid != os.getuid():
        _deny(f"{what} must be owned by uid {os.getuid()}")
    if st.st_size > REHEARSAL_MAX_FILE:
        _deny(f"{what} is too large")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        data = f.read(REHEARSAL_MAX_FILE + 1)
    if not data.isascii() or b"//" in data or b"/*" in data:
        _deny(f"{what} must be plain ASCII JSON without comments")

    def pairs(items):
        keys = [k for k, _ in items]
        if len(keys) != len(set(keys)):
            _deny(f"{what} has duplicate keys")
        return dict(items)

    def constant(name):
        _deny(f"{what} contains {name}")

    try:
        value = json.loads(data.decode("ascii"), object_pairs_hook=pairs, parse_constant=constant)
    except ValueError:
        _deny(f"{what} is not valid JSON")

    def walk(v):
        if v is None:
            _deny(f"{what} contains null")
        if isinstance(v, str) and not v.isascii():
            _deny(f"{what} decodes to non-ASCII text")
        if isinstance(v, dict):
            for k, item in v.items():
                walk(k)
                walk(item)
        if isinstance(v, list):
            for item in v:
                walk(item)
    walk(value)
    if type(value) is not dict:
        _deny(f"{what} must be one JSON object")
    return value, data


def _check_path(value, key: str):
    if type(value) is not str or not value or not value.startswith("/") or "~" in value \
            or os.path.normpath(value) != value:
        _deny(f"config {key} must be a non-empty absolute normalised path without ~")
    if not _real_inside(value, REHEARSAL_ROOT):
        _deny(f"config {key} is outside {REHEARSAL_ROOT}")


def _check_config(config: dict):
    for key, value in config.items():
        kind = _CONFIG_SCHEMA.get(key)
        if kind is None:
            _deny(f"config key {key!r} is not allowed")
        if kind == "path":
            _check_path(value, key)
        elif kind == "strlist":
            if type(value) is not list or any(type(v) is not str for v in value):
                _deny(f"config {key} must be a list of strings")
        elif kind is int:
            if type(value) is not int or not 0 <= value <= 1000:
                _deny(f"config {key} must be an integer 0..1000")
        elif kind in (bool, str):
            if type(value) is not kind:
                _deny(f"config {key} must be {kind.__name__}")
        elif kind == "endpoints":
            if type(value) is not dict:
                _deny("config FileSystemPublishEndpoints must be an object")
            for name, endpoint in value.items():
                if type(endpoint) is not dict or "rootDir" not in endpoint \
                        or set(endpoint) - {"rootDir", "linkMethod"}:
                    _deny(f"endpoint {name!r} must have rootDir and at most linkMethod")
                _check_path(endpoint["rootDir"], f"FileSystemPublishEndpoints.{name}.rootDir")
                if "linkMethod" in endpoint and endpoint["linkMethod"] not in ("hardlink", "symlink", "copy"):
                    _deny(f"endpoint {name!r} linkMethod is not allowed")
        elif kind == "database":
            if type(value) is not dict or set(value) - {"type", "dbPath"}:
                _deny("config databaseBackend may only have type and dbPath")
            if "type" in value and value["type"] != "leveldb":
                _deny("config databaseBackend type must be exactly leveldb")
            if "dbPath" in value:
                _check_path(value["dbPath"], "databaseBackend.dbPath")
        elif kind == "pool":
            if type(value) is not dict or set(value) - {"type", "path"}:
                _deny("config packagePoolStorage may only have type and path")
            if "type" in value and value["type"] != "local":
                _deny("config packagePoolStorage type must be exactly local")
            if "path" in value:
                _check_path(value["path"], "packagePoolStorage.path")
    if "rootDir" not in config:
        _deny("config must set rootDir")


def _check_root():
    st = os.lstat(REHEARSAL_ROOT)
    if not stat.S_ISDIR(st.st_mode):
        _deny(f"{REHEARSAL_ROOT} must be a directory, not a link")
    _owned_private(st, REHEARSAL_ROOT)
    real = os.path.realpath(REHEARSAL_ROOT)
    if real != REHEARSAL_ROOT or _inside(real, LIVE_APTLY) or _inside(LIVE_APTLY, real):
        _deny(f"{REHEARSAL_ROOT} must not resolve elsewhere or overlap {LIVE_APTLY}")
    with open(MOUNTINFO, encoding="utf-8") as f:
        for line in f:
            point = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), line.split()[4])
            if _inside(point, REHEARSAL_ROOT):
                _deny(f"a mount point is at or under {REHEARSAL_ROOT}")
    links: dict = {}
    count = 0

    def fail(error):
        raise error

    for top, dirs, files in os.walk(REHEARSAL_ROOT, onerror=fail, followlinks=False):
        for name in dirs + files:
            count += 1
            if count > REHEARSAL_MAX_ENTRIES:
                _deny(f"{REHEARSAL_ROOT} has too many entries")
            path = os.path.join(top, name)
            st = os.lstat(path)
            if stat.S_ISLNK(st.st_mode):
                if not _inside(os.path.realpath(path), REHEARSAL_ROOT):
                    _deny(f"{path} links outside {REHEARSAL_ROOT}")
            elif stat.S_ISDIR(st.st_mode):
                _owned_private(st, path)
            elif stat.S_ISREG(st.st_mode):
                key = (st.st_dev, st.st_ino)
                links[key] = (st.st_nlink, links.get(key, (0, 0))[1] + 1)
            else:
                _deny(f"{path} is not a regular file, directory or link")
    for nlink, seen in links.values():
        if nlink != seen:
            _deny(f"a file in {REHEARSAL_ROOT} has hard links outside it")


def _check_marker(session_id: str | None) -> tuple[dict, str]:
    st = os.lstat(REHEARSAL_COORDINATOR)
    if not stat.S_ISDIR(st.st_mode):
        _deny(f"{REHEARSAL_COORDINATOR} must be a directory, not a link")
    _owned_private(st, REHEARSAL_COORDINATOR)
    if not os.path.lexists(REHEARSAL_MARKER):
        _deny("no rehearsal authorization is recorded (C writes it after May's approval)")
    if os.path.realpath(REHEARSAL_MARKER) != REHEARSAL_MARKER:
        _deny("the rehearsal authorization must not resolve elsewhere")
    marker, data = _strict_json(REHEARSAL_MARKER, "the rehearsal authorization")
    if set(marker) != _MARKER_KEYS:
        _deny(f"the rehearsal authorization must have exactly {sorted(_MARKER_KEYS)}")
    if marker["schema"] != 1 or type(marker["schema"]) is not int:
        _deny("the rehearsal authorization has an unknown schema")
    for key in _MARKER_KEYS - {"schema"}:
        if type(marker[key]) is not str or not marker[key]:
            _deny(f"the rehearsal authorization {key} must be a non-empty string")
    if marker["root"] != REHEARSAL_ROOT or marker["authorized_by"] != "May" or marker["recorded_by"] != "C":
        _deny("the rehearsal authorization is not May's, recorded by C, for the rehearsal root")
    if not session_id or marker["session_id"] != session_id:
        _deny("the rehearsal authorization belongs to another session")
    stamps = []
    for key in ("not_before", "not_after"):
        if not _UTC_STAMP.match(marker[key]):
            _deny(f"the rehearsal authorization {key} must be YYYY-MM-DDTHH:MM:SSZ")
        from datetime import datetime, timezone
        stamps.append(datetime.strptime(marker[key], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
    import time
    if not stamps[0] < stamps[1] or stamps[1] - stamps[0] > REHEARSAL_MAX_WINDOW:
        _deny("the rehearsal authorization window must be positive and at most 24 hours")
    if not stamps[0] <= time.time() < stamps[1]:
        _deny("the rehearsal authorization is not valid now")
    import hashlib
    return marker, hashlib.sha256(data).hexdigest()


def _log_rehearsal(command: str, session_id: str, marker: dict, marker_sha: str):
    fd = os.open(REHEARSAL_LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            _deny("the rehearsal log must be a regular file")
        _owned_private(st, "the rehearsal log")
        from datetime import datetime, timezone
        line = json.dumps({"time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "session_id": session_id, "task_id": marker["task_id"],
                           "reference": marker["reference"], "command": command,
                           "marker_sha256": marker_sha}) + "\n"
        os.write(fd, line.encode("ascii"))
    finally:
        os.close(fd)


def _rehearsal_candidate(command: str) -> bool:
    """A command meant as a rehearsal: aptly with a config flag and publish."""
    tokens = command.split()
    return bool(tokens) and os.path.basename(tokens[0]) == "aptly" \
        and any(t.lstrip("-").startswith("config") for t in tokens[1:]) and "publish" in tokens


def _check_rehearsal(command: str, session_id: str | None):
    if not _REHEARSAL_SHAPE.match(command):
        _deny("one plain command only: no quoting, expansion, redirection or separators")
    tokens = command.split(" ")
    if tokens[0] != APTLY_BINARY:
        _deny(f"call aptly as {APTLY_BINARY}")
    st = os.lstat(APTLY_BINARY)
    on_path = _which("aptly")
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022 \
            or not on_path or not os.path.samefile(on_path, APTLY_BINARY):
        _deny(f"{APTLY_BINARY} must be the root-owned aptly on PATH")
    args = tokens[1:]
    if any(".." in a for a in args):
        _deny("no argument may contain ..")
    configs = [i for i, a in enumerate(args) if a.lstrip("-").startswith("config")]
    if len(configs) != 1 or not (args[configs[0]].startswith("-config=") or args[configs[0]].startswith("--config=")):
        _deny("exactly one -config=PATH (or --config=PATH) is required")
    # No other global flag: one written as `-flag value` would make the
    # value the command word (Go's flag parser, aptly cmd/cmd.go).
    if len(args) < 2 or configs[0] != 0 or args[1] != "publish":
        _deny("the command must start: -config=PATH publish")
    if any(_DENIED_WORD.search(a) for a in args[2:] if not a.startswith("-")):
        _deny("publish, task or api may appear only as the command word")
    path = args[0].split("=", 1)[1]
    if not path.startswith(REHEARSAL_ROOT + "/") or os.path.normpath(path) != path:
        _deny(f"the config must be an absolute normalised path inside {REHEARSAL_ROOT}")
    _check_root()
    config, _ = _strict_json(path, "the config file")
    _check_config(config)
    marker, marker_sha = _check_marker(session_id)
    _log_rehearsal(command, session_id, marker, marker_sha)


# --- live-phase allowance (UNITY-20260929-008) ---------------------------------
#
# ENGINEERING-PROCESS section 6: for the live phase of a task May authorized,
# only the exact command strings of the reviewed list are admitted, byte for
# byte, as one foreground Bash call, through C's dated live marker (a separate
# file and key set from the rehearsal marker). The pinned aptly config must be
# unchanged. Every admitted command is logged. Known limit: a shell function
# in the agent's own profile could stand in for the binary; the guard refuses
# only when it finds one. Design and review:
# docs/research/UNITY-20260929-008-live-allowance/.

LIVE_COMMANDS = "/home/claude/unity-distro/.claude/hooks/live-commands.json"
LIVE_CONFIG = "/home/claude/.aptly.conf"
LIVE_MARKER = REHEARSAL_COORDINATOR + "/live-authorization.json"
LIVE_LOG = REHEARSAL_COORDINATOR + "/live-log.jsonl"
LIVE_MAX_WINDOW = 6 * 3600
LIVE_PREFIX = APTLY_BINARY + " -config=" + LIVE_CONFIG + " publish "
LIVE_HOME = "/home/claude"
LIVE_SHELL_FILES = (".bashrc", ".profile", ".bash_profile", ".bash_aliases")
LIVE_SNAPSHOTS = ".claude/shell-snapshots"
_LIVE_LIST_KEYS = {"schema", "task_id", "root", "aptly_conf_sha256", "commands"}
_LIVE_MARKER_KEYS = {"schema", "kind", "task_id", "root", "authorized_by", "recorded_by",
                     "not_before", "not_after", "reference", "session_id", "commands_sha256"}
_LIVE_KIND = "live-publish"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
# A function or alias named *aptly* anywhere on a line (Claude Code's shell
# snapshots define functions as eval $'name () \n{ ... }'), an exported
# BASH_FUNC_*aptly*, BASH_ENV, a DEBUG/RETURN trap, or a dynamic-loader
# variable that would run code inside the aptly binary.
_SHADOW = re.compile(r"function\s+\S*aptly|[^\s'\"$]*aptly\S*\s*\(\s*\)|\balias\s+\S*aptly"
                     r"|BASH_FUNC_\S*aptly|BASH_ENV|\btrap\b.*\b(?:DEBUG|RETURN)\b"
                     r"|\bLD_(?:PRELOAD|LIBRARY_PATH|AUDIT)\b")
_SHADOW_ENV = ("BASH_ENV", "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT")


def _sha256_hex(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _check_aptly_binary():
    st = os.lstat(APTLY_BINARY)
    on_path = _which("aptly")
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022 \
            or not on_path or not os.path.samefile(on_path, APTLY_BINARY):
        _deny(f"{APTLY_BINARY} must be the root-owned aptly on PATH")


def _live_list() -> tuple[dict, str]:
    # A git checkout file (umask 0002 gives 0664); its integrity comes from
    # the marker's commands_sha256, so only owner and file type are checked.
    listing, data = _strict_json(LIVE_COMMANDS, "the live command list", private=False)
    if set(listing) != _LIVE_LIST_KEYS or listing["schema"] != 1 or type(listing["schema"]) is not int:
        _deny(f"the live command list must have exactly {sorted(_LIVE_LIST_KEYS)} and schema 1")
    if type(listing["task_id"]) is not str or not listing["task_id"] or listing["root"] != LIVE_APTLY:
        _deny(f"the live command list must name a task and the root {LIVE_APTLY}")
    if type(listing["aptly_conf_sha256"]) is not str or not _SHA256.match(listing["aptly_conf_sha256"]):
        _deny("the live command list aptly_conf_sha256 must be a sha256")
    commands = listing["commands"]
    if type(commands) is not list or not commands or len(set(commands)) != len(commands) \
            or any(type(c) is not str or not _REHEARSAL_SHAPE.match(c) or not c.startswith(LIVE_PREFIX)
                   for c in commands):
        _deny(f"the live command list must hold unique plain commands starting {LIVE_PREFIX!r}")
    return listing, _sha256_hex(data)


def _check_live_config(listing: dict):
    config, data = _strict_json(LIVE_CONFIG, "the live aptly config")
    if _sha256_hex(data) != listing["aptly_conf_sha256"]:
        _deny(f"{LIVE_CONFIG} differs from the reviewed one")
    if config.get("rootDir") != LIVE_APTLY:
        _deny(f"the live aptly config rootDir must be {LIVE_APTLY}")
    for key in ("S3PublishEndpoints", "SwiftPublishEndpoints", "AzurePublishEndpoints",
                "FileSystemPublishEndpoints"):
        if config.get(key, {}) != {}:
            _deny(f"the live aptly config must not have {key}")
    for key in ("databaseBackend", "packagePoolStorage"):
        if key in config:
            _deny(f"the live aptly config must not set {key}")


def _check_live_shell():
    """Best effort: refuse when the agent's shell setup could shadow aptly."""
    for name in _SHADOW_ENV:
        if os.environ.get(name):
            _deny(f"{name} is set")
    paths = [os.path.join(LIVE_HOME, name) for name in LIVE_SHELL_FILES]
    snapshots = os.path.join(LIVE_HOME, LIVE_SNAPSHOTS)
    if os.path.isdir(snapshots):
        paths += [os.path.join(snapshots, name) for name in sorted(os.listdir(snapshots))]
    for path in paths:
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            text = f.read(4 * 1024 * 1024).decode("utf-8", "replace")
        if _SHADOW.search(text):
            _deny(f"{path} defines an aptly function or alias, BASH_ENV, a DEBUG/RETURN trap "
                  "or a dynamic-loader variable")


def _check_live_marker(session_id: str | None, listing: dict, list_sha: str) -> tuple[dict, str]:
    st = os.lstat(REHEARSAL_COORDINATOR)
    if not stat.S_ISDIR(st.st_mode):
        _deny(f"{REHEARSAL_COORDINATOR} must be a directory, not a link")
    _owned_private(st, REHEARSAL_COORDINATOR)
    if not os.path.lexists(LIVE_MARKER):
        _deny("no live authorization is recorded (C writes it after May's GO and the L0 record)")
    if os.path.realpath(LIVE_MARKER) != LIVE_MARKER:
        _deny("the live authorization must not resolve elsewhere")
    marker, data = _strict_json(LIVE_MARKER, "the live authorization")
    if set(marker) != _LIVE_MARKER_KEYS:
        _deny(f"the live authorization must have exactly {sorted(_LIVE_MARKER_KEYS)}")
    if marker["schema"] != 1 or type(marker["schema"]) is not int:
        _deny("the live authorization has an unknown schema")
    for key in _LIVE_MARKER_KEYS - {"schema"}:
        if type(marker[key]) is not str or not marker[key]:
            _deny(f"the live authorization {key} must be a non-empty string")
    if marker["kind"] != _LIVE_KIND:
        _deny(f"the live authorization kind must be {_LIVE_KIND}")
    if marker["root"] != LIVE_APTLY or marker["authorized_by"] != "May" or marker["recorded_by"] != "C" \
            or marker["task_id"] != listing["task_id"]:
        _deny("the live authorization is not May's, recorded by C, for this task and the live root")
    if marker["commands_sha256"] != list_sha:
        _deny("the live authorization names another command list")
    if not session_id or marker["session_id"] != session_id:
        _deny("the live authorization belongs to another session")
    from datetime import datetime, timezone
    import time
    stamps = []
    for key in ("not_before", "not_after"):
        if not _UTC_STAMP.match(marker[key]):
            _deny(f"the live authorization {key} must be YYYY-MM-DDTHH:MM:SSZ")
        stamps.append(datetime.strptime(marker[key], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
    if not stamps[0] < stamps[1] or stamps[1] - stamps[0] > LIVE_MAX_WINDOW:
        _deny("the live authorization window must be positive and at most 6 hours")
    if not stamps[0] <= time.time() < stamps[1]:
        _deny("the live authorization is not valid now")
    return marker, _sha256_hex(data)


def _log_live(command: str, session_id: str, tool_name: str, marker: dict, marker_sha: str, list_sha: str):
    fd = os.open(LIVE_LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            _deny("the live log must be a regular file")
        _owned_private(st, "the live log")
        from datetime import datetime, timezone
        line = json.dumps({"time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "event": "admitted", "session_id": session_id, "task_id": marker["task_id"],
                           "tool_name": tool_name, "cwd": os.getcwd(), "command": command,
                           "marker_sha256": marker_sha, "commands_sha256": list_sha}) + "\n"
        if os.write(fd, line.encode("ascii")) != len(line):
            _deny("the live log write was incomplete")
    finally:
        os.close(fd)


def _check_live(command: str, session_id: str | None, tool_name: str | None, background: bool):
    if tool_name != "Bash" or background:
        _deny("live commands run only as a foreground Bash call")
    listing, list_sha = _live_list()
    if command not in listing["commands"]:
        _deny("not an exact entry of the reviewed live command list")
    _check_aptly_binary()
    _check_live_config(listing)
    _check_live_shell()
    marker, marker_sha = _check_live_marker(session_id, listing, list_sha)
    _log_live(command, session_id, tool_name, marker, marker_sha, list_sha)


# --- trusted files (permission model phase 3) -------------------------------------
#
# The trusted set lives once, in scripts/install_command_guard.py, which also
# writes the Edit/Write ask rules for it. A shell write into one of those
# files by a listed form is refused here; the Edit tool is the way, and it
# asks May. sudoers writes and visudo are refused outright. Design:
# docs/research/permission-model-2026-10-09/phase3-permissions-block.md

_TRUSTED = None
_UNKNOWN_DIR = object()  # the working directory after a cd that is not a literal
_FD_DUP = re.compile(r"^&(\d+|-)$")  # "2>&1" reaches rule 1 as the target "&1": no file is written
_SHELLS = {"sh", "bash", "dash", "zsh", "ksh", "su"}  # su -c runs its string through a shell
# Wrappers Claude Code strips before matching its own permission rules.
_WRAPPERS = {"timeout", "nice", "nohup", "stdbuf", "time", "setsid", "ionice"}
_WRAPPER_VALUE_OPTIONS = {"timeout": {"-s", "--signal", "-k", "--kill-after"}, "nice": {"-n", "--adjustment"},
                          "ionice": {"-c", "--class", "-n", "--classdata", "-p"}, "stdbuf": {"-i", "-o", "-e"},
                          "time": {"-f", "--format", "-o", "--output"}, "nohup": set(), "setsid": set()}


def _trusted_set():
    """(files, dirs, globs, sudoers) from the installer next to this guard's checkout,
    executed from its source text (never a bytecode cache). A failure raises and
    fails the hook closed."""
    global _TRUSTED
    if _TRUSTED is None:
        installer = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                 "scripts", "install_command_guard.py")
        with open(installer, "rb") as handle:
            source = handle.read()
        namespace = {"__name__": "install_command_guard_trusted", "__file__": installer}
        exec(compile(source, installer, "exec"), namespace)
        _TRUSTED = (tuple(namespace["TRUSTED_FILES"]), tuple(namespace["TRUSTED_DIRS"]),
                    tuple(namespace["TRUSTED_GLOBS"]), tuple(namespace["SUDOERS_PATHS"]))
    return _TRUSTED


_HOME_VAR = re.compile(r"^\$(HOME|\{HOME\})(?=/|$)")
_COPIERS_DEST = {"cp", "mv", "install", "rsync", "ln"}
_REMOVERS = {"rm", "shred", "unlink", "truncate", "gzip", "bzip2", "xz", "zstd"}
# a bytecode cache under a trusted directory is not trusted state
_CACHE_PATH = re.compile(r"(/__pycache__(/|$)|\.pyc$)")
_INTERP_WORD = re.compile(r"^(python[0-9.]*|perl|ruby|node|php)$")
_WRITE_IDIOMS = re.compile(
    r"(?:\bopen\s*\(([^()]*)\))|(?:\bPath\s*\(([^()]*)\)\s*\.\s*write_(?:text|bytes))|"
    r"(?:\b(?:shutil\.(?:copy\w*|move)|os\.(?:replace|rename|link|symlink))\s*\(([^()]*)\))")
_MODE_WRITE = re.compile(r"['\"](?:w|a|w\+|a\+|wb|ab|wt|at)['\"]")


def _unwrap_writer(tokens: list[str]) -> list[str]:
    """Leading shell words ({ if then while ! time ...), _unwrap, then the wrappers
    Claude Code itself strips (timeout 5 cp ... is cp ...)."""
    while tokens and tokens[0] in _SHELL_WORDS:
        tokens = tokens[1:]
    tokens = _unwrap(tokens)
    while tokens:
        word = os.path.basename(tokens[0])
        if word not in _WRAPPERS:
            return tokens
        i = 1
        while i < len(tokens) and tokens[i].startswith("-"):
            i += 2 if tokens[i] in _WRAPPER_VALUE_OPTIONS[word] else 1
        if word == "timeout":
            i += 1  # the duration
        tokens = _unwrap(tokens[i:])
    return tokens


def _resolve_path(token: str, base=None):
    """[absolute, real] candidates for a token that may name a file, resolved
    against base (the session directory, moved by a leading cd); None when the
    token is not a resolvable literal (another variable, a substitution)."""
    if not token or SUBST in token or "`" in token:
        return None
    home = os.path.expanduser("~")
    text = token
    if text == "~" or text.startswith("~/"):
        text = home + text[1:]
    text = _HOME_VAR.sub(home, text)
    if "$" in text:
        return None
    if not os.path.isabs(text):
        if base is _UNKNOWN_DIR:
            return None
        text = os.path.join(base or os.getcwd(), text)
    absolute = os.path.normpath(text)
    try:
        real = os.path.realpath(absolute)
    except OSError:
        real = absolute
    return [absolute] if real == absolute else [absolute, real]


def _is_trusted_path(path: str, include_sudoers: bool = True):
    files, dirs, globs, sudoers = _trusted_set()
    if _CACHE_PATH.search(path):
        return None
    if path in files or any(fnmatch.fnmatchcase(path, g) for g in globs):
        return "trusted"
    if any(path == d or path.startswith(d + "/") for d in dirs):
        return "trusted"
    if include_sudoers and any(path == d or path.startswith(d + "/") for d in sudoers):
        return "sudoers"
    return None


def _is_trusted_ancestor(path: str):
    """A directory whose removal or move takes a trusted file with it."""
    files, dirs, globs, sudoers = _trusted_set()
    candidates = list(files) + list(dirs) + [os.path.dirname(g) for g in globs] + list(sudoers)
    for candidate in candidates:
        if candidate != path and candidate.startswith(path.rstrip("/") + "/") and path not in ("/", os.path.expanduser("~")):
            return "sudoers" if candidate in sudoers or any(candidate.startswith(d + "/") for d in sudoers) else "trusted"
    return None


def _is_trusted_parent(path: str):
    """A directory into which files of unknown names land (an archive, a download):
    a trusted directory, inside one, or the directory holding a trusted file."""
    kind = _is_trusted_path(path)
    if kind:
        return kind, path
    if path.rstrip("/") in ("", os.path.expanduser("~")):
        return None  # as _is_trusted_ancestor: the home itself is not a trusted directory
    files, dirs, globs, sudoers = _trusted_set()
    for candidate in list(files) + list(globs) + list(sudoers):
        if os.path.dirname(candidate) == path.rstrip("/"):
            return ("sudoers" if candidate in sudoers else "trusted"), candidate
    return None


def _classify_targets(tokens: list[str], ancestors: bool = False, base=None):
    for token in tokens:
        for path in _resolve_path(token, base) or ():
            kind = _is_trusted_path(path) or (_is_trusted_ancestor(path) if ancestors else None)
            if kind:
                return kind, path
    return None


def _classify_directory(directory, names: list[str], base=None):
    """Files named `names` written into `directory`; unknown names (empty list)
    count when the directory is trusted or holds a trusted file."""
    for path in _resolve_path(directory, base) or ():
        for name in names:
            kind = _is_trusted_path(os.path.join(path, name))
            if kind:
                return kind, os.path.join(path, name)
        if not names:
            found = _is_trusted_parent(path)
            if found:
                return found
    return None


def _url_name(url: str) -> str:
    path = url.split("://", 1)[-1].split("?", 1)[0].split("#", 1)[0]
    return os.path.basename(path.rstrip("/")) or "index.html"


def _option_values(args: list[str], flags: tuple) -> list[str]:
    values = []
    for n, a in enumerate(args):
        if a in flags and n + 1 < len(args):
            values.append(args[n + 1])
        elif any(a.startswith(f + "=") for f in flags if f.startswith("--")):
            values.append(a.split("=", 1)[1])
    return values


def _write_targets(group: list[str], base=None):
    """(kind, path) of the first trusted file this group writes by a listed form, else None."""
    tokens = _unwrap_writer(group)
    if not tokens:
        return None
    word = os.path.basename(tokens[0])
    args = [t for t in tokens[1:] if t != HEREDOC]
    redirects = _redirect_targets(group)
    if redirects:
        found = _classify_targets([t for t in redirects if t != "/dev/null" and not _FD_DUP.match(t)], base=base)
        if found:
            return found
    if word == "visudo":
        return "sudoers", "visudo"
    operands = [a for a in args if not a.startswith("-") and not _REDIRECT.match(a)]
    if word == "tee":
        return _classify_targets(operands, base=base)
    if word in _COPIERS_DEST:
        if "-t" in args:
            index = args.index("-t")
            dest = args[index + 1] if index + 1 < len(args) else None
            sources = [o for o in operands if o != dest]
        elif len(operands) >= 2:
            dest, sources = operands[-1], operands[:-1]
        else:
            return _classify_targets(operands, ancestors=word == "mv", base=base)
        found = _classify_targets(sources, ancestors=word == "mv", base=base)  # a trusted source moved away
        if found and word == "mv":
            return found
        resolved = _resolve_path(dest, base) if dest else None
        if not resolved:
            return None
        candidates = []
        for path in resolved:
            if dest.endswith("/") or os.path.isdir(path):
                candidates += [os.path.join(path, os.path.basename(src.rstrip("/"))) for src in sources]
            candidates.append(path)
        for path in candidates:
            kind = _is_trusted_path(path)
            if kind:
                return kind, path
        return None
    if word == "dd":
        return _classify_targets([a.split("=", 1)[1] for a in args if a.startswith("of=")], base=base)
    if word == "sed" and any(a.startswith("-") and not a.startswith("--") and "i" in a[1:]
                            or a.startswith("--in-place") for a in args):
        return _classify_targets(operands, base=base)
    if word in _REMOVERS:
        return _classify_targets(operands, ancestors=True, base=base)
    if word == "curl":
        found = _classify_targets(_option_values(args, ("-o", "--output")), base=base)
        if found:
            return found
        if any(a in ("-O", "--remote-name", "--remote-name-all") or a.startswith("-") and not a.startswith("--")
               and "O" in a[1:] for a in args):
            names = [_url_name(o) for o in operands if "://" in o]
            return _classify_directory(".", names, base) if names else None
        return None
    if word == "wget":
        outputs = _option_values(args, ("--output-document",))
        for n, a in enumerate(args):
            if a.startswith("-") and not a.startswith("--") and "O" in a[1:]:
                rest = a[a.index("O") + 1:]
                outputs.append(rest if rest else args[n + 1] if n + 1 < len(args) else "-")
        if outputs:
            return _classify_targets([o for o in outputs if o != "-"], base=base)
        names = [_url_name(o) for o in operands if "://" in o or "." in o]
        prefixes = _option_values(args, ("-P", "--directory-prefix")) or ["."]
        for prefix in prefixes:
            found = _classify_directory(prefix, names, base)
            if found:
                return found
        return None
    if word == "tar":
        extracting = any(a.startswith("-") and not a.startswith("--") and "x" in a[1:] or a in ("--extract", "--get")
                         for a in args) or (operands and args and operands[0] == args[0] and "x" in operands[0])
        if extracting:
            directories = _option_values(args, ("-C", "--directory")) or ["."]
            for directory in directories:
                found = _classify_directory(directory, [], base)
                if found:
                    return found
        return None
    if word == "unzip":
        directories = _option_values(args, ("-d",)) or ["."]
        for directory in directories:
            found = _classify_directory(directory, [], base)
            if found:
                return found
        return None
    return None


def _interpreter_writes(text: str, base=None):
    """A trusted literal next to a write idiom in interpreter code (a heredoc body or a -c string)."""
    for match in _WRITE_IDIOMS.finditer(text):
        kind = "open" if match.group(1) is not None else "path" if match.group(2) is not None else "shutil"
        inside = match.group(1) or match.group(2) or match.group(3) or ""
        if kind == "open" and not _MODE_WRITE.search(inside):
            continue
        for literal in re.findall(r"""['"]([^'"]+)['"]""", inside):
            for path in _resolve_path(literal, base) or ():
                found = _is_trusted_path(path)
                if found:
                    return found, path
    return None


def _deny_trusted(found) -> str:
    kind, path = found
    return DENY_MESSAGES["sudoers"] if kind == "sudoers" else DENY_MESSAGES["trusted"].format(path=path)


def _option_string(tokens: list[str], letter: str) -> str | None:
    """The argument of -c (a shell or interpreter string) or -e, also in a cluster such as -ec."""
    for n, token in enumerate(tokens[1:], 1):
        if token.startswith("-") and not token.startswith("--") and letter in token[1:] and n + 1 < len(tokens):
            return tokens[n + 1]
    return None


class _Cwd:
    """The working directory while walking one level's groups: a leading cd moves
    it, pushd/popd keep a stack, a ")" ends a subshell's cd."""

    def __init__(self, base):
        self.base, self.here, self.stack = base, base, []

    def step(self, tokens: list[str], sep: str):
        word = os.path.basename(tokens[0]) if tokens else ""
        if word in ("cd", "pushd"):
            targets = [t for t in tokens[1:] if not t.startswith("-") or t == "-"]
            if word == "pushd":
                self.stack.append(self.here)
            if not targets:
                self.here = os.path.expanduser("~") if word == "cd" else self.here
            else:
                resolved = _resolve_path(targets[0], self.here) if targets[0] != "-" else None
                self.here = resolved[0] if resolved else _UNKNOWN_DIR
        elif word == "popd":
            self.here = self.stack.pop() if self.stack else _UNKNOWN_DIR
        return word

    def end_group(self, sep: str):
        if ")" in sep:
            self.here, self.stack = self.base, []


def _trusted_rules(levels: list, command: str, base=None, depth: int = 0) -> str | None:
    """Permission model phase 3, rules 1 and 3, over every executed group of the
    outer and substitution levels, following a leading cd, into shell -c strings,
    heredoc bodies (with the directory current at their owner) and interpreter
    code; readers of trusted files are untouched."""
    if depth > MAX_DEPTH:
        return None
    for level in levels:
        if level.blob or level.body:
            continue  # bodies are walked below with the directory current at their owner
        cwd = _Cwd(base)
        for group, sep in zip(level.groups, level.seps):
            tokens = _unwrap_writer(group)
            word = cwd.step(tokens, sep)
            if word not in ("cd", "pushd", "popd"):
                found = _write_targets(group, cwd.here)
                if found:
                    return _deny_trusted(found)
                if word in _SHELLS:
                    text = _option_string(tokens, "c")
                    if text:
                        message = _nested_shell(text.replace(QUOTED_GT, ">"), cwd.here, depth)
                        if message:
                            return message
                if _INTERP_WORD.match(word):
                    for letter in ("c", "e"):
                        text = _option_string(tokens, letter)
                        found = _interpreter_writes(text, cwd.here) if text else None
                        if found:
                            return _deny_trusted(found)
            cwd.end_group(sep)
    # heredoc bodies: the scanner's raw bodies, each at its owner's directory
    try:
        scanner = _Scanner(command)
        outer = scanner.run()
        groups, seps = _lex(outer)
    except (ScanError, ValueError):
        return None
    cwd = _Cwd(base)
    owners = []
    unwrapped = [_unwrap_writer(group) for group in groups]
    for n, (group, sep) in enumerate(zip(groups, seps)):
        tokens = unwrapped[n]
        cwd.step(tokens, sep)
        runner = _body_runner(group, tokens)
        m = n
        while runner is None and _pipes(seps[m]) and m + 1 < len(groups):
            m += 1  # cat <<EOF | tee /tmp/s.sh | bash: the runner is anywhere down the pipeline
            runner = _body_runner(groups[m], unwrapped[m])
        owners += [(runner, cwd.here) for token in group if token == HEREDOC]
        cwd.end_group(sep)
    for n, body in enumerate(scanner.bodies):
        runner, here = owners[n] if n < len(owners) else (None, base)
        if runner == "interpreter":
            found = _interpreter_writes(body.text, here)
            if found:
                return _deny_trusted(found)
        elif runner == "shell":
            message = _nested_shell(body.text, here, depth)
            if message:
                return message
    return None


def _body_runner(group: list[str], tokens: list[str]) -> str | None:
    """How a command runs text handed to it: "shell" (sh, bash, su, a leading
    shell word, or sudo -s / sudo -i with no command), "interpreter", or None (data)."""
    tokens = [t for t in tokens if t != HEREDOC]
    word = os.path.basename(tokens[0]) if tokens else ""
    if _INTERP_WORD.match(word):
        return "interpreter"
    if word in _SHELLS or word in _SHELL_WORDS:
        return "shell"
    if not tokens:
        rest = [t for t in group if t not in _SHELL_WORDS and t != HEREDOC]
        if rest and os.path.basename(rest[0]) == "sudo":
            return "shell"
    return None


def _nested_shell(text: str, here, depth: int) -> str | None:
    """Rule 1 over shell text run by a shell -c string or a shell heredoc."""
    try:
        nested = _levels(text)
    except ScanError:
        return None  # a text the shell itself rejects runs nothing
    return _trusted_rules(nested, text, here, depth + 1)


_PARSE_MESSAGE = "Command guard could not parse shell quoting; tool call blocked."
_GLOB_CHARS = re.compile(r"[*?\[]")


def _unguarded(token: str) -> bool:
    stripped = _GUARDED_PARAMETER.sub("", token)
    return bool(_VARIABLE_EXPANSION.search(stripped)) or bool(_GLOB_CHARS.search(stripped))


def _rm_recursive_forced(tokens: list[str]) -> tuple[bool, list[str]]:
    options = [t for t in tokens[1:] if t.startswith("-") and t != "--"]
    paths = [t for t in tokens[1:] if not t.startswith("-")]
    return (any(_is_option(t, "rR", "--recursive") for t in options)
            and any(_is_option(t, "f", "--force") for t in options)), paths


def _dash_f_like(token: str) -> bool:
    return token == "-" or token == "--full" or (token.startswith("-") and not token.startswith("--") and "f" in token[1:])


def _fallback_refusals(groups: list[list[str]], second: bool) -> str | None:
    """Permission model phase 1, RC1 steps 5 and 6: forms a quote-hidden
    separator can produce on the fallback path. Step 5 (second lexing only):
    an rm -rf without a path, or pkill/pgrep with a lone dash. Step 6 (both
    lexings): rm -rf, pkill/pgrep, git add and git push judged together with
    the first token of the following group, the one the separator orphaned."""
    for n, group in enumerate(groups):
        tokens = _unwrap(group)
        if not tokens:
            continue
        base = os.path.basename(tokens[0])
        following = groups[n + 1][0] if n + 1 < len(groups) and groups[n + 1] else None
        if base == "rm":
            dangerous, paths = _rm_recursive_forced(tokens)
            if dangerous and second and not paths:
                return _PARSE_MESSAGE
            if dangerous and following is not None and _unguarded(following):
                return DENY_MESSAGES["remove"]
        if base in ("pkill", "pgrep"):
            if second and any(t == "-" for t in tokens[1:]):
                return _PARSE_MESSAGE
            if following is not None and _dash_f_like(following):
                return DENY_MESSAGES["process"]
        if base == "git" and len(tokens) > 1 and following is not None:
            if tokens[1] == "add" and following in ("-A", "--all", ".", "docs", "docs/"):
                return DENY_MESSAGES["stage"]
            if tokens[1] == "push" and (_is_option(following, "f", "--force")
                                        or following.startswith("--force-with-lease") or following.startswith("+")):
                return DENY_MESSAGES["push"]
    return None


def _fallback_floor(command: str) -> str | None:
    """Permission model phase 1 (UNITY-20260929-003 RC1): when the whole-text
    floor cannot lex the command (an apostrophe in a quoted heredoc body or a
    prose line), the text is lexed twice with the guard's own lexer, once
    without apostrophes and once without apostrophes, double quotes and
    backslashes; a text that does not lex in either form is refused as before;
    every group rule, and the step-5/6 refusals, apply to both lexings.
    Design: docs/research/permission-model-2026-10-09/phase1-guard-false-positives.md"""
    joined = command.replace("\\\n", "")
    try:
        first, _ = _lex(joined.replace("'", ""))
        second, _ = _lex(joined.replace("'", "").replace('"', "").replace("\\", ""))
    except ValueError:
        return _PARSE_MESSAGE
    return (_group_rules(first) or _group_rules(second)
            or _fallback_refusals(first, False) or _fallback_refusals(second, True))


def inspect(command: str, session_id: str | None = None, tool_name: str | None = "Bash",
            background: bool = False, cwd: str | None = None) -> str | None:
    # Permission model phase 3: the trusted set must load (else fail closed) and
    # relative paths resolve against the session's directory.
    _trusted_set()
    if cwd and os.path.isdir(cwd):
        try:
            os.chdir(cwd)
        except OSError:
            pass
    # Live phase: only an exact reviewed string, checked before the floor.
    if command.startswith(LIVE_PREFIX):
        try:
            _check_live(command, session_id, tool_name, background)
        except (RehearsalDenied, OSError, ValueError) as error:
            return f"aptly live command not allowed: {error}"
        return None
    # The earlier tokenisation stays as a floor: UNITY-20260927-058 only adds denials.
    # When it cannot lex the text, the phase-1 fallback decides instead of refusing.
    legacy = _legacy_groups(command)
    fallback = legacy == [["<parse-error>"]]
    message = _fallback_floor(command) if fallback else _group_rules(legacy)
    if message:
        return message
    try:
        levels = _levels(command, fallback=fallback)
    except ScanError:
        return _PARSE_MESSAGE
    rest = _group_rules(group for level in levels if not level.body for group in level.groups) \
        or _trusted_rules(levels, command)
    if _rehearsal_candidate(command):
        try:
            _check_rehearsal(command, session_id)
        except (RehearsalDenied, OSError, ValueError) as error:
            return f"aptly rehearsal not allowed: {error}"
        return rest
    return _aptly_rules(levels) or rest


def _group_rules(groups) -> str | None:
    for raw in groups:
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
        # A Monitor with a WebSocket source runs no shell.
        if payload.get("tool_name") == "Monitor" and isinstance(tool_input, dict) and "ws" in tool_input:
            return 0
        print("Command guard found no shell command; tool call blocked.", file=sys.stderr)
        return 2
    try:
        session = payload.get("session_id")
        tool_name = payload.get("tool_name")
        cwd = payload.get("cwd")
        message = inspect(command, session if isinstance(session, str) else None,
                          tool_name if isinstance(tool_name, str) else None,
                          tool_input.get("run_in_background") not in (None, False),
                          cwd if isinstance(cwd, str) else None)
    except Exception as error:  # fail closed on any bug in the guard itself
        message = f"Command guard failed ({type(error).__name__}); tool call blocked."
    if message:
        print(message, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
