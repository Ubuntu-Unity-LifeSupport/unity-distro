# UNITY-20260927-058: command_guard.py lets `aptly publish` through in other forms

Owner: agent B (builder; the board lists `target-desktop-2`). Split by the
coordinator from UNITY-20260927-057: tighten `.claude/hooks/command_guard.py`
so that no form of `aptly publish` passes - `-config X`, `--config=`,
`-config=`, `HOME`/`APTLY_CONFIG`, `env`/`sudo`/`command`/absolute-path
wrappers, symlinks, `..`. Tightening only: nothing is allowed that is denied
today. UNITY-20260927-057 (a narrow allowance for a rehearsal config) will be
added on top later and must not have to rewrite the check. Found during
UNITY-20260927-047; the bypass was reported, never used.

```yaml
task_id: UNITY-20260927-058
package: unity-distro .claude/hooks/command_guard.py
target_series: resolute
issue: local - the Bash guard matches `aptly publish` only as aptly's first argument
status: REPRODUCED
issue_search_result: NOT_FOUND  # project-local hook
source_version: origin/main 03f5cea
binary_version: aptly 1.6.2-2 (builder)
source_commit: 03f5cea
observed: >
  logs/01-reproduction.txt: of 51 commands that reach aptly's publish command,
  run aptly commands the hook cannot inspect (task run, api serve) or copy the
  aptly binary under another name, the current hook allows 40 - every global
  flag before `publish`, timeout/nice/nohup/setsid/stdbuf/xargs, bash -c,
  eval, $(...), backticks, subshells and groups, sudo -u, command, exec, an
  absolute path followed by a flag.
expected: >
  Every such form is denied; aptly reads (repo/snapshot/config/serve/version)
  and unrelated commands still pass.
reproduction: logs/01-reproduction.txt; scripts/tests/test_command_guard.py
root_cause: >
  inspect() takes the command word after a short list of prefixes (_unwrap) and
  denies only `args[0] == "publish"`. aptly's parser (smira/commander
  ParseFlags, first pass with c.mergedFlags) accepts flags of every aptly
  command before and between command words, so `publish` can be preceded by
  any number of flags; the command word can also sit behind any wrapper the
  hook does not list, inside a nested shell string or a command substitution.
  aptly itself can run publish without the word following it: `aptly task run`
  executes aptly commands from arguments, a file or stdin, and `aptly api serve`
  exposes POST/PUT/DELETE /api/publish.
root_cause_mechanism: >
  position-based matching of one token against an argument grammar that does
  not fix that position
root_cause_evidence: >
  aptly-1.6.2 cmd/cmd.go:95-126 (global flags), context/context.go:91-100
  (config: -config, else $HOME/.aptly.conf, /usr/local/etc, /etc; no
  APTLY_CONFIG), cmd/task_run.go, cmd/api_serve.go; commander
  commands.go:194-262 (merged flags, command path)
invariant: >
  A Bash command that can make aptly run its publish command is denied,
  whatever flags, wrappers, nesting or binary name surround it.
existing_fix_result: NOT_FIXED
candidate_approaches:
  - (A) recognise aptly anywhere in a command, deny if any bare argument
    token (not starting with "-") is publish, task or api; recurse into
    nested shell strings - chosen
  - (B) model aptly's flag grammar (which flags take a value) to find the
    exact command word - rejected: the merged flag set is every flag of every
    aptly command (dozens, version-dependent); a wrong entry turns a value
    into a command word or the reverse, in both directions
  - (C) deny every aptly invocation that has any flag before the command
    word - rejected: still misses wrappers and nesting, and blocks
    `aptly -config=... snapshot list`, which 047 needs for read-only checks
  - (D) replace the aptly binary on PATH with a wrapper - rejected: out of
    scope (the hook is the agreed control); changes the system for every user
  - (E) allow-list of aptly's first command word (repo, snapshot, mirror,
    package, db, config, serve, version, graph) - added to A after design
    review round 1: closes publish produced by expansion, xargs/find and
    git-style external subcommands
chosen_approach: F (see Design) - A's word rule applied to the whole command, E for literal invocations, an allow-list of readers for any other mention
why_chosen: >
  aptly's command path consists of bare tokens; publish, task and api are
  never valid as anything else in our usage, so matching them anywhere among
  aptly's arguments is independent of the flag grammar. A false positive
  (a snapshot named "publish", a flag value "api") is denied - fail closed.
design_challenger_required: true
design_review_result: APPROVE  # rounds 1-4 REVISE, round 5 APPROVE, see Design review
architectural_task: false
correct_layer: >
  the hook is the project's Bash-level safety net for aptly publish (ENGINEERING-PROCESS section 9);
  scripts/publish_aptly.py calls aptly via subprocess and is not affected
defensive_workaround_rejected: >
  adding more first-argument patterns (e.g. args[1] == "publish") keeps the
  position assumption that caused the bypass
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # hook I/O contract (stdin JSON, exit 2 + stderr) unchanged
unknowns:
  - outside what a tokenising hook can see (ENGINEERING-PROCESS section 9
    calls it best-effort): a variable or alias as the command word ($A
    publish; aliases from an earlier call), the binary written under another
    name by redirection (cat /usr/bin/aptly > x) and run in a later call,
    interpreters that build the words at run time (python -c with string
    concatenation), a relative path to a copy made from another directory,
    a heredoc written to a script file and run in a later line, a command
    word built by expansion with no literal aptly or publish in the command
    (a=ap; b=tly; $a$b $c), an aptly API server started outside this hook
    reached with curl (none runs; api serve is denied), text encoded for an
    interpreter (printf with octal escapes piped to bash, base64), a script
    written by the Write tool and run later, a command built only from
    expansions (${a}ly ${b}lish)
  - part E of the verification (adversarial search for bypasses) is NOT
    VERIFIED: the environment's safety classifier stopped every attempt to
    write adversarial cases. Residual risk: a form outside the tested cases
    may pass through a mechanism no adversarial test exercised (scanner,
    heredoc classification, _exposed(), reader list, prefixes). Follow-up:
    UNITY-20260928-002 (backlog)
  - scripts/taskctl.py, listed as a reader, runs `aptly publish show`
    itself (read-only, from the publication record, when moving a task to
    PUBLISHED). It passes none of its arguments to a shell. Section 6's
    Aptly freeze allows that call only inside an authorized publication
    workflow
```

## Reproduction

`scripts/tests/test_command_guard.py` runs the hook exactly as Claude Code
does (JSON on stdin, exit 2 = deny). `logs/01-reproduction.txt` is the result
against origin/main: 40 of the 51 must-deny commands pass, all 16 must-allow
commands pass.

Facts from the aptly 1.6.2 source (`apt-get source aptly`) that the tests
encode:

- Config: `-config` (any flag form Go's `flag` accepts: `-config=X`,
  `-config X`, `--config=X`, `--config X`), otherwise `$HOME/.aptly.conf`,
  `/usr/local/etc/aptly.conf`, `/etc/aptly.conf`. aptly reads no
  `APTLY_CONFIG`; `HOME` matters only without `-config`.
- Command path: commander's `ParseFlags` parses with the merged flag set of
  all commands before each command word, so `aptly -distribution x -batch
  publish ...` is valid.
- `aptly task run` runs aptly commands given as arguments, in a file
  (`-filename`) or on stdin; `aptly api serve` serves the REST API including
  publishing. Neither is used by the project (grep of scripts/, docs/,
  .claude/).

## Design review round 1: REVISE

The Design Challenger (read-only subagent; tokenisation checked with shlex and
the current hook, aptly and commander sources read) found:

1. Newlines are whitespace to the current lexer: `true<NL>aptly publish list`
   is one command whose word is `true` (also a hole for the git and rm rules).
2. Shell expansion makes `publish` out of other text: `aptly $'publish'`,
   `aptly {publish,}`, `p=publish; aptly $p`, a glob, a function
   (`f(){ aptly "$@"; }; f publish`), `echo publish | xargs aptly`,
   `find -name publish -exec aptly {} \;`, and aptly's git-style external
   subcommands (`aptly foo` runs `aptly-foo`, commander commands.go:292-300).
   Command names are matched exactly, no abbreviations (commands.go:225,281).
3. Quoted scripts run by other programs: `su -c`, `ssh host '...'`,
   `runuser -c`, `script -c`, `flock -c`, `watch`, `tmux`, `python3 -c`.
4. Recursing into every `$(...)` would deny Claude Code's own commit form
   (`git commit -m "$(cat <<'EOF' ... EOF)"`) and any doc written through a
   heredoc that mentions `aptly publish`.
5. Identify aptly by file identity (`os.path.samefile`), not `realpath`
   string equality (hard links).
6. Record for 057 whether the aptly call is literal.

Also checked: `aptly serve` only serves the public dir (cmd/serve.go:100),
`db cleanup` only reads publications (cmd/db_cleanup.go:132); only
`publish *`, `task run` and `api serve` publish - the three words are
complete. Alternative (E), added from the review: an allow-list of aptly's
first command word on top of A's anywhere-deny.

## Design review round 2: REVISE

Fixed: newline separation, file identity, `literal` for 057. New findings:
(1) the 057 handoff was wrong - a config without `rootDir` uses
`$HOME/.aptly` (utils/config.go:216) and `~` in `rootDir` expands through
`HOME` (utils/config.go:325), so `HOME` matters even with `-config`;
(2) several "readers" execute strings: `git -c core.pager=...`,
`git -c alias.x='!...'`, `GIT_PAGER=`, `dpkg --pre-invoke=`,
`apt-get -o APT::Update::Pre-Invoke::=...`, `LESSOPEN=`, `rg --pre`,
`git bisect run`; (3) a wrapper list for quoted strings is never complete
(`nsenter`, `chroot`, `systemd-run`, `bwrap`, `busybox`, ...); (4) heredoc
cutting must be exact or it hides real commands: `<<` only unquoted, not
`<<<`, several per line in order, quote removal on the delimiter, tabs only
for `<<-`, deny an unparseable delimiter, and the whole logical line counts
(`cat <<EOF | bash`); (5) the single-quote skip needs a real quote-state
scanner (`echo "it's $(aptly publish list)"`); (6) `cat /usr/bin/aptly > x`
escapes the copy rule through a reader.

## Design (approach F, after round 2)

Round 2 showed that every list of what *runs* a string (wrappers, readers
with hooks, interpreters) is open-ended. Approach F therefore needs only
lists of what is *allowed*, and treats the words themselves as the signal.

**Step 1 - scan.** A quote-aware scanner (contexts: plain, `'...'`,
`$'...'`, `"..."`, `$(...)`, backticks, `\` escapes; backslash-newline
removed) splits the text into the outer text and the texts of `$(...)` and
backticks outside single quotes, which are processed recursively (depth 8,
deeper is denied). In plain and `$(...)` context it finds heredocs: `<<` or
`<<-` (not `<<<`, not inside quotes or `$((...))`), delimiter with quote
removal (`"E"`, `E'O'F`, `\EOF`, `cat<<EOF`), bodies taken in order from the
lines after the operator's line, leading tabs stripped only for `<<-`; a
delimiter that cannot be parsed is denied.

**Step 2 - heredoc bodies.** A body is *text only* when its delimiter is
quoted and the heredoc's logical line (from the line start, or from the
enclosing `$(`, to the line end, heredoc operators removed) lexes to exactly
one command group whose command word is `cat` and that does not end in a
separator (`|`, `&&`, `||`, `;` or `&`). That is the Claude Code commit form
`git commit -m "$(cat <<'EOF' ... EOF)"` and `cat > file <<'EOF'`. A
text-only body is removed. Every other body is processed as a script (step 1
recursively). An unquoted delimiter's body is not text-only, since it
expands.

**Step 3 - lexing.** Whitespace is space, tab and CR. Newline, `(` and `)`
join `;&|` as separators. This is a general fix that also covers the git and
rm rules.

**Step 4 - is aptly involved?** Yes when any of these holds:
- the remaining text (all levels, text-only bodies removed) contains the
  word `aptly`, with word boundaries that exclude `[A-Za-z0-9_.-]` (so
  `publish_aptly.py`, `.aptly.conf` and `aptly047` do not count);
- any lexed token has basename `aptly`;
- any lexed token is the same file (`os.path.samefile`, device and inode) as
  `aptly` on PATH.

**Step 5 - rules when aptly is involved.**
- *Rule A (words).* The word `publish`, `task` or `api` anywhere, either in
  the text (same boundaries) or as a lexed token at any level, means deny.
  This covers any wrapper, reader hook, remote or interpreter string without
  listing them (`ssh h 'aptly publish'`, `git -c core.pager='aptly publish'`,
  `python3 -c "...('aptly publish')"`, `LESSOPEN=...`).
- *Rule E (literal invocations).* A group whose command word, after the
  existing prefixes (`command`, `builtin`, `exec`, `sudo`, `env`,
  assignments) and the shell words `{ ! time if then elif else while until
  do`, is aptly (step 4) must have, as its first bare argument after skipping
  flags and the value of a space-separated `-config`/`--config`, one of
  `repo snapshot mirror package db config serve version graph`, spelled with
  `[a-z]` only. A missing, unknown or expanded word (`$p`, `$publish`,
  `{publish,}`, `publis?`, `{}`, `foo` -> `aptly-foo`, a flag value such as
  `amd64`) is denied.
- *Rule R (any other mention).* An aptly occurrence that is not the command
  word of a group checked by rule E is allowed only when **every** group of
  the command (all levels) is a reader: `grep`, `egrep`, `fgrep`, `ls`,
  `stat`, `file`, `sha256sum`, `sha1sum`, `md5sum`, `readlink`, `realpath`,
  `dpkg-query`, `apt-cache` (without `-o`, `--option`, `-c`,
  `--config-file`), `which`, `type`, `command -v`/`-V`, `echo`, `printf`,
  `head`, `tail`, `wc`, `sort`, `uniq`, `cut`, `cat`, `test`, `[`, and `git`
  without `-c`, `--config-env` or `--exec-path` and with subcommand `commit`,
  `log`, `show`, `diff`, `status`, `grep`, `blame`, `ls-files`, `add` or
  `rev-parse`. Reader groups may have no assignments and no output
  redirection other than to `/dev/null`. So `timeout 60 aptly repo list`,
  `xargs aptly`, `find -exec aptly`, `nsenter ... aptly`, `f publish` (a
  function) and `cat /usr/bin/aptly > x` are denied, while `grep -n aptly f`,
  `ls /usr/bin/aptly`, `apt-cache policy aptly` and
  `git commit -m 'docs: aptly snapshot notes'` pass.
- *Rule C (copies).* A group whose command word is `cp`, `ln`, `install`,
  `mv`, `rsync`, `dd` or `tee` and that names the aptly binary is denied.
  With rule R this is already covered, but it gets its own message.

**Step 6 - decision point for 057.** `_aptly_call()` for each rule-E group
returns the bare words, the command word, the config values in all four flag
forms in order, the assignments and `env` arguments in front of it, and
`literal`. `_aptly_denial()` holds rules A, E, R and C. 057 adds an allowance
for `publish` there, and only there. `task` and `api` stay denied.

**Known false positives (fail closed).**
- Any Bash command that mentions both aptly and publish, task or api is
  denied, for example `git commit -m '... aptly publish ...'` or a grep for
  both words. The alternatives are a commit message through the heredoc form,
  or Claude Code's Grep and Read tools, which the hook does not inspect.
- Wrappers are denied around aptly: `timeout 60 aptly repo list`.
- `aptly -architectures amd64 snapshot list` is denied; use
  `-architectures=amd64`.
- Programs outside the reader list that name aptly are denied: `man aptly`,
  `apt show aptly`, `dpkg -L aptly`. Use `dpkg-query -L`.

**Handoff to 057 (corrected).** Allow `publish` only when all of these
hold:
- the whole command is that single aptly group, with no separators, no
  nesting and no heredoc;
- `literal` is true;
- there is exactly one `-config`, an absolute path that resolves
  (`realpath`) into the rehearsal location;
- the config file sets an explicit absolute `rootDir` without `~`, inside the
  rehearsal location;
- no `FileSystemPublishEndpoints`, S3 or Swift endpoints point elsewhere;
- `HOME` is not overridden in front of aptly (`call.env`).

## Design review round 3: REVISE, and the changes to F

1. *aptly spelled without the word:* `{apt,-architectures=}ly publish ...`,
   `/usr/bin/apt?y publish`, `$'\x61ptly' publish`, `a=apt; ${a}ly publish`,
   `$(printf apt)ly publish`. Change: the scanner decodes `$'...'` before
   lexing and matching, and sets `expansion` when it sees, outside single
   quotes, `$` followed by a name, `{`, `(`, a digit or one of `@*#?!$-`, or
   a backtick, and, in plain context, `*`, `?`, `[` or a brace group with `,`
   or `..`. Rule A applies when aptly is involved **or** `expansion` is set:
   a command with any expansion and the word publish, task or api is denied.
2. *Executed commit-form heredoc:* `bash -c "$(cat <<'EOF' ... EOF)"`.
   Change: a body is text only when, in addition, every group of the
   command outside the body (all levels) is a reader (rule R), except that
   the heredoc's own `cat` group may redirect its output to a file, provided
   it has no file operands.
3. *Readers that execute or write:* the reader definition excludes git
   `-O`/`--open-files-in-pager`, `--output`, `--ext-diff`, `--textconv`;
   sort `-o`/`--output`/`--compress-program`; `printf -v`; uniq with a
   second operand; and any output redirection (`>`, `>>`, `>|`, `&>`, with
   or without an fd number) other than to `/dev/null` or to another fd
   (`>&2`).
4. *Occurrences, defined:* an occurrence is a lexed token, at any level,
   whose text contains the aptly word, has basename `aptly`, or is the same
   file as aptly. Tokens in text-only heredoc bodies are never lexed.
   Everything else is lexed: the outer text with substitutions replaced by a
   placeholder, and each substitution text recursively. An occurrence that
   is not the command word of a group passing rule E goes to rule R. Test:
   `aptly version; bash -c 'aptly $(printf pub)lish list'`.

057 handoff additions: `realpath` of `rootDir` and of every
`FileSystemPublishEndpoints` root must lie in the rehearsal location; a
missing or unparsable config file is denied.

Additional known false positive: any command with an expansion (a variable,
a glob, a brace group) and the word publish, task or api, for example
`grep -n publish "$f"`. Additional unknowns: text encoded for an interpreter
(`printf '\141ptly ...' | bash`, base64), files written by the Write tool
and run later, a command word built only from expansions with no literal
publish/task/api (`${a}ly ${b}lish`).

## Design review round 4: REVISE (one change)

All round-3 changes were confirmed against their findings, and so was rule A
against commander letting a flag consume a command word
(`aptly -distribution repo publish list` is denied by the literal `publish`).
One new class was found: the hook is registered for the `Bash` tool only
(`.claude/settings.json`, `"matcher": "Bash"`). Claude Code's `Monitor` tool
runs a `command` string "in the same shell environment as Bash" (its tool
schema, checked in this session), so `Monitor({command: "aptly ... publish
..."})` never reaches the hook.

Changes:
- `.claude/settings.json`: the matcher becomes `Bash|Monitor`. This is
  tightening only: one more tool is checked by the same rules.
- `main()`: a `Monitor` call with `ws` and no `command` (a WebSocket, no
  shell) is allowed. A call with neither `command` nor `ws` is still denied.
- A test sends a Monitor-shaped payload through the hook.
- ENGINEERING-PROCESS section 9 names both tools.
- Other tools in this session take structured input, not shell text. Bash
  with `run_in_background` is the same Bash tool. Subagents use the project
  settings.
- Optional, taken: a copy through a glob (`ln -s /usr/bin/apt?y
  ~/.local/bin/zz`). Round 5 refined the rule: see below.

## Design review round 5: APPROVE

The `Bash|Monitor` matcher is a valid regex over tool names (the documented
`Edit|Write` form). `main()`'s Monitor handling and its tests are complete.
Non-blocking suggestion, taken: the glob-copy rule "mentions apt" is too weak
(`/usr/bin/a?tly`, `/usr/bin/[a]ptly`). Instead, each token with unquoted
glob characters is expanded with `glob.glob`, and every match gets the
`samefile` test. A match is an aptly occurrence, so rules E, R and C apply
exactly as for a literal path. The "mentions apt" trigger is dropped. Brace
groups keep the expansion rule.

## Implementation

`.claude/hooks/command_guard.py`, `.claude/settings.json` (matcher
`Bash|Monitor`), `scripts/tests/test_command_guard.py`,
`docs/ENGINEERING-PROCESS.md` section 9.

- **The earlier tokenisation is a floor.** `inspect()` first applies the
  existing git/xwd/pkill/rm/publish rules to the pre-058 tokenisation, then
  to the new one. By construction nothing the old hook denied is allowed
  (`logs/04-corpus.txt`: 0).
- **`_Scanner`** is the quote-aware pass from the design, with heredocs,
  `$'...'` decoding and the `expansion` flag. A `>` inside quotes is marked
  so it is not taken for a redirection.
- **`_lex`** returns commands with the separator after each. It rejoins
  `2>&1`, `>&2` and `&>file`, which shlex splits at `&`.
- **`_collect`** records, for each substitution, the command it is an
  argument of.
- **`_levels`** classifies each heredoc body:
  - *TEXT (not inspected):* its owner is a reader (for example
    `cat > file`, or `git commit -F -`) or a loop keyword with only readers
    around, and the output reaches no runner. That means no pipe, the level
    is the top level or a `git commit`/`tag` message, and no runner uses the
    file written.
  - *BLOB (one token):* its owner is `python`, `perl`, `ruby`, `node`,
    `php` and the like, and the body can start a process (`subprocess`,
    `system(`, `exec*(`, `eval(`, ...; backticks for perl, ruby and php), or
    the owner is `cat`/`tee` whose output does reach a runner.
  - *SCRIPT (shell, all rules):* everything else. A body that does not
    parse as shell becomes a BLOB.
  - An unquoted body's `$(...)` and backticks are always inspected.
- **`_aptly_rules`**:
  - A command with no aptly occurrence and no expansion is left alone.
  - A literal aptly command goes to rule E (`_aptly_call`,
    `_aptly_denial`): no publish/task/api among its arguments, and an
    allowed first command word.
  - Rule C (copies) is checked by file identity only.
  - Every other command that is not a reader is a *runner*. `_exposed()`
    finds the commands whose words can reach a runner: the runner itself,
    commands piping into it, substitutions it consumes, assignments when a
    runner expands a variable, and files written that a runner names.
  - In exposed text, the words publish/task/api together with an aptly
    occurrence or an expansion deny. An aptly occurrence alone denies.
  - With no runner, nothing is denied: readers and literal aptly commands
    cannot run anything else.
- **Occurrences** are the name `aptly` as a command name (not
  `publish_aptly.py`, `.aptly.conf`, `aptly047`, `-aptly-` or a directory
  such as `/srv/aptly`), or any path, glob or PATH name that is the aptly
  binary by device and inode.
- **Monitor.** A `Monitor` call is checked like Bash. A WebSocket-only call
  (`ws`, no `command`) passes.
- **Cost.** 58 ms per call against 52 ms before (no dataclasses/shutil
  imports; `glob` only when a token has a glob).

## Result

- **Tests.** `scripts/tests/test_command_guard.py`: 7 tests covering 127
  must-deny commands, 43 must-allow commands, symlink and hard-link
  identity, the Monitor tool and its settings entry, and the other rules.
  Before the fix, 71 of the round-1 cases fail (`logs/02-tests-before-fix.txt`;
  the later rounds only add cases). After the fix, all pass, and so does the
  full suite of 43 tests (`logs/03-tests-after.txt`).
- **Real commands** (`logs/04-corpus.txt`, `corpus.py`). All 4544 unique
  Bash/Monitor commands from the builder's Claude Code transcripts were
  replayed through both versions (the commands are parsed, never run).
  - 0 commands that the old hook denied are allowed now.
  - 88 commands the old hook allowed are denied now:
    - 46 are the existing git/rm/pkill/quoting rules applied to lines the
      old hook could not see: a newline was whitespace to it, and it did
      not look inside `$(...)`. Examples: `git add docs` or `git add -A` on
      a later line, `rm -rf $SP/...`, `pgrep -f` in `$(...)`.
    - 8 are real `aptly publish` calls from 2026-09-22/23 on a later line
      of a command.
    - The remaining ~34 are the accepted false positives listed below.

**Known false positives (fail closed), measured on the corpus:**
- Scripts written through `cat > f <<EOF` and run by a later command in the
  same call, when they mention aptly.
- Python heredocs that mention aptly and start processes.
- `apt-get install ... aptly ...` and `apt-get source aptly`.
- `ssh host '...aptly...'`.
- `gh api .../$n` and other commands where a runner has both a variable and
  the words `api`, `task` or `publish`.
- `aptly -architectures amd64 ...` (use `=`).
- `timeout`, `xargs` or `bash -c` around aptly.
- A variable holding an aptly command (`A="aptly ..."; $A ...`).

## Verification

Verdict by part (`verification.md`): A PASS, B PASS, C PASS, D PASS,
**E NOT VERIFIED**, F PASS. Review status REVIEWED.

- **Bounds of what was checked:** 127 must-deny tests, 41 C/D cases, 36
  documented forms, and 4566 real commands with no newly allowed command.
- **Not claimed:** full adversarial or security coverage. The residual risk
  and the follow-up UNITY-20260928-002 are listed under unknowns.
- **Also added on the owner's decision:** the Aptly freeze rule in
  ENGINEERING-PROCESS section 6.

## Status

DONE (not a package task). Merge by the coordinator. The DECISIONS entry
is added at merge time.
