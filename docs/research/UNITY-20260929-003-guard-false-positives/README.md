# UNITY-20260929-003 - command_guard false positives

Kind: `tool` (`.claude/hooks/command_guard.py`). Owner: B. May confirmed the
task in B's session b7902aab, with this scope: narrow false positives only;
fail-closed and all aptly rules kept.

History: paused 2026-09-29 ~14:55Z for UNITY-20260927-021 and resumed at
~19:40Z.

## Reproduction

`denials.py` collects every refusal of the guard from the Claude Code
transcripts, read-only. On 2026-09-29 19:4xZ it found 44 refusals.

An isolated subagent classified each one by calling the worktree guard's
`inspect()` on the command as data; nothing was executed. Result (in
`corpus/denials-classified.json`):

- **10 true positives:**
  - `pgrep -f` / `pgrep -af` (7);
  - `git add -A` (1);
  - `aptly publish list` through another path (2).
- **3 collector artefacts.**
- **31 false positives.** Today's guard gives the recorded reason for all
  41 real records.

The three cases C added on 2026-09-29 are in the corpus: records 13 and 15
("task"/"publish" as data with `$(date)`), records 4 and 43 ("publish" in a
`python3 -c` that reads a gate), and record 30 (`sed` with `/srv/aptly`).

## Root causes

Line numbers refer to `command_guard.py` at 3d8d991.

| ID | Records | Cause | In this task |
|---|---|---|---|
| RC1 | 13 | The legacy floor (`_legacy_groups`, 794-809, used at 1297) tokenises the whole text with shlex, heredoc bodies included. An apostrophe in a quoted-delimiter body is "No closing quotation", so the call is refused before the heredoc-aware scanner runs. The scanner parses all 16 heredoc records. | yes |
| RC1b | 3 (6, 24, 35) | `git commit -F - <<'EOF'` is classed SCRIPT, because git has operands (`_classify_body`, 637-648). Its body is scanned as shell, although git only reads it as the message. | yes (needed with RC1) |
| RC4 | 2 (11, 13) | `sed` counts as a reader only for p/d/= scripts (588-593), so any `s///` makes it a runner. | yes, narrow |
| RC5 | 1 (30) | The `/srv/aptly` exemption (487-492) covers only a token that is exactly the directory. Inside `s\|x\|/srv/aptly\|p` or `--root=/srv/aptly`, it still matches `_APTLY_TEXT`. | yes |
| RC2 | 10 | `python3 -c CODE` is always a runner, so string literals in CODE count as mentions and words. | no: follow-up |
| RC3 | (with RC2/RC4) | Expansion is tracked per level, not per command. An accepted false positive (058 README). | no |
| RC6 | 1 (36) | `awk` is not a reader. | no: follow-up |
| RC7 | 1 (10) | `ssh host 'command -v aptly'` is an opaque runner. An accepted false positive. | no |

Why RC2 and RC6 are left out: making `python3 -c` or `awk` a reader means
judging a program in another language statically. Both can start processes
(`os.system`, `subprocess`, awk `system()`, `| getline`). That widens the
boundary more than "narrow false positives only" allows. They are proposed
to C as a separate decision.

## Existing fix

`NOT_FIXED`:

- main (3d8d991 merge of origin/main) has the legacy floor unchanged.
- No other branch changes `command_guard.py` against main.
- UNITY-20260927-058's README lists RC3 and RC7 as accepted false positives,
  not RC1.

## Invariant

Everything the guard denies today, it keeps denying. A call is allowed only
when every command the shell can run from the text has been seen and passed
every rule. Text that is never run (heredoc bodies read as data, commit
messages) is not tokenised as shell.

## Related security fix

The Design Challenger's round 1 found a separate hole in how heredoc bodies
are classified. It is handled first, as UNITY-20260929-018, and described
there after the merge. Step 0 below refers to that fix.

## Chosen approach (round 2, after the Design Challenger's REVISE)

0. **TEXT only when nothing can run the body.** A heredoc body is TEXT only
   if all of these hold, in addition to today's conditions:
   - its level has no group that is `{`, `(`, `)`, `}` or a function
     definition;
   - no separator in the level pipes into a group that is not a reader;
   - no runner anywhere in the call carries an expansion or a glob.
   Otherwise the body is read as SCRIPT or BLOB, as today for a piped
   owner.
1. **RC1: a legacy floor that never fails.** When shlex fails on the whole
   text, apply the same legacy group rules line by line:
   - `\`-newline continuations are joined first;
   - each line is lexed as today;
   - a line that does not lex is split on whitespace and `;&|`, with the
     quote characters removed.
   It does not depend on how bodies are classified. Every denial the old
   floor made on a line is kept: an `it's` line carries no rule tokens, and
   a `pkill -f` line in a body is still seen. After the floor, the
   heredoc-aware scanner (`_levels`) runs unchanged for the aptly rules. A
   scan error there is still "could not parse".
2. **RC1b.** A body owned by `git commit` or `git tag` that reads its
   message from stdin (`-F -`, `-F-`, `--file=-`, `--file -`) is TEXT, under
   the conditions of step 0 and today's TEXT conditions. git never runs the
   message: hooks, `--template` and `--cleanup` only read it.
3. **RC4.** `sed` is also a reader when all of these hold:
   - each argument is an exact option `-n`, `-E`, `-r`, `-i`, `-s`, `-z` or
     `-u` (no combined short options, no `-i.bak`, `--in-place=`, `-e`,
     `-f`, `--expression` or `--debug`), an existing file, or one
     substitution script;
   - the script fully matches (`re.fullmatch`)
     `s<d>((?:\\.|[^\\\n<d>])*)<d>((?:\\.|[^\\\n<d>])*)<d>[gIip0-9]*`,
     where the delimiter `<d>` is one character that is not alphanumeric, a
     backslash, a newline or whitespace;
   - the script contains neither aptly nor publish/task/api, because
     `sed -i` writes files that `_exposed` does not follow.
4. **RC5.** `_is_aptly` removes the text `/srv/aptly` before its tests, only
   where both of these hold:
   - it is preceded by the start of the token, `=`, `:`, a quote or `,`;
   - it is followed by the end, `/`, `|`, `:`, a quote, a space, `,` or
     `;)]`.
   Only the matched text is removed, never the whole token, and never from
   the command word. So `/srv/aptly;aptly publish`,
   `/srv/aptly/../../usr/bin/aptly` and `/tmp/srv/aptly -config=x publish`
   still count, and `_same_as_aptly` (the inode check) still runs.

## Correct layer

`command_guard.py`, where the refusals come from:

- the order of floor and scanner in `inspect`;
- `_classify_body`;
- `_is_reader`;
- `_is_aptly`.

`settings.json` and the fail-closed wrapper are not touched.

## Tests

`scripts/tests/test_command_guard.py`:

- the 31 false positives' minimal forms (RC1, RC1b, RC4, RC5 cases) are
  added to ALLOWED;
- a must-still-deny set is added to DENIED:
  - `bash <<'EOF'` with `pkill -f`, and with an unterminated quote;
  - `cat <<'EOF' | sh` with a publish line in the body;
  - `sed 's/x/aptly publish list/e'`, `sed -e ...` and `sed 's/a/b/w f'` with
    aptly;
  - `/srv/aptly/bin/aptly publish list`;
  - a heredoc body plus `git add -A` / `rm -rf $X` in the same call;
- every existing DENIED and ALLOWED entry stays.
