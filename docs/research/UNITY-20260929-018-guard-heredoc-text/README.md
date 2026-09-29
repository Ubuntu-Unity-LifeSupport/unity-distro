# UNITY-20260929-018 - command_guard: a heredoc body the shell runs was classed as text

Kind: `tool` (`.claude/hooks/command_guard.py`), SECURITY. Owner: B. Found by
the Design Challenger of UNITY-20260929-003. The coordinator assigned it
separately, to be merged before UNITY-20260929-003.

## Reproduction

The Design Challenger of UNITY-20260929-003 found the problem (rounds 1
and 2, 2026-09-29) by calling the guard's `inspect()` on command strings as
data. Nothing was executed.

On main 1173de0, `inspect()` returns None (allow) for commands in which:

- a heredoc body contains an aptly publish command, or `pkill -f`;
- the shell does run that body, because a compound command, a function
  wrapper or a process substitution pipes it into a shell, or because a
  file written with it is run later in the same call.

The exact forms are the must-still-deny cases in
`scripts/tests/test_command_guard.py`, under the comment
UNITY-20260929-018.

## Existing fix

`NOT_FIXED`:

- main 1173de0 has the code described below;
- no branch changes `_classify_body`;
- UNITY-20260927-058's list of accepted false positives does not cover
  this, because it is a false negative.

## Root cause

`_classify_body` calls a body TEXT, so it is never scanned, when its owner
is a reader, the level is sink-safe, and the owner's own separator does not
pipe.

Mechanism, in `_levels` and `_classify_body`:

- `_lex` makes `(` and `)` separators, and `{`/`}` are ordinary groups. A
  pipe that follows a closing `)` or `}`, or a function's call, is not the
  owner's separator, so the pipe into the shell goes unseen.
- A body written to a file counts only when the file's basename appears
  literally in another runner's token. A glob, a copy, a quoted-apart name
  or a git hook runs it without that.

## Invariant

A heredoc body is TEXT only when nothing in the call can run it. Otherwise
it is inspected: as SCRIPT when a shell reads it, or as BLOB, whose words
the aptly rules see.

## Chosen approach (tightening only)

Keep every TEXT condition that exists today, and add four more. A body is
TEXT only if all of these hold:

1. No separator of its level contains `(` or `)`, and no group of the
   level starts with `{` or `}`. This covers subshells, brace groups,
   function definitions and process substitution.
2. No separator of its level pipes into a group that is not a reader.
3. No runner (non-reader group) in the whole call carries an expansion, a
   substitution or a glob (`$`, `*`, `?`, `[`).
4. Any group of the owner's level writes a file (redirect targets other than
   `/dev/null`, including a redirect on `done`/`fi` or an `exec` redirect)
   is allowed only if all of these hold:
   - the whole call has no runner at all;
   - no target has `.git` as a path component, or a basename `config`,
     `.gitconfig`, `.gitattributes` or `.gitmodules`;
   - no token in the call names `hooksPath`;
   - no `cd` or `ln` in the call has an operand with `.git` as a path
     component.

When any of these fails, the body goes to the existing SCRIPT/BLOB rules:
`cat`/`tee` become BLOB. When condition 4 is what failed, the blob is
marked `forced`. The aptly rules then check its words even when the call
has no runner, because git runs hooks, fsmonitor and aliases itself, and
`chmod` and `git commit` count as readers. Nothing that is denied today
becomes allowed.

Design Challenger round 1 (REVISE) found the hook form (no runner), the
redirect on another group of the level, and hook or config paths reached
by `cd`, a symlink, `.git/config` or `.gitattributes`. Condition 4 and
`forced` are the changes for those findings.

Design Challenger round 2: **APPROVE**. Its mock denies every form from both
rounds. It leaves ALLOWED and DENIED unchanged. It found that `forced` only
adds checks.

- Taken from round 2: the bare `hooks` path component is dropped, because
  it denied doc writes under `docs/hooks` and `.claude/hooks`. `.git`, the
  git basenames, `hooksPath` and the `cd`/`ln` rule cover the hook forms.
- Known limit (round 2): a heredoc that writes `.claude/settings.json` or
  `.claude/hooks/*` takes effect only on a later tool call. That is the same
  as using the Write tool, so it is outside this guard.

Implementation note: condition 4 was first applied to the targets of every
group of the level. The replay then denied 84 real commands. In those, a
sibling group such as `sed ... > /tmp/t` made an unrelated `python3 -`
body forced, although that body is never written to the file. Condition 4
now takes its targets only from the groups that receive the owner's
output:

- the owner itself;
- an earlier `exec` redirection;
- a closing `done`, `fi`, `esac` or `}` after the owner.

Every must-deny form stays denied.

## Validation (2026-09-29)

- logs/02: full suite, 201 tests, OK, 1 skipped.
  `test_heredoc_text_only_when_nothing_runs_it` runs the hook on 22 forms
  from `scripts/tests/data/command_guard_018_must_deny.json`:
  - 20 must be denied;
  - 2 `ok-` doc writes under `hooks` directories must be allowed;
  - 1 `ctl-` control has nothing forbidden in its body.
  Every existing DENIED and ALLOWED entry is unchanged.
- logs/01: replay of all 7712 distinct real Bash/Monitor commands from the
  transcripts, through `inspect()` of main and of this branch. Result:
  - 18 go from allow to deny, 0 from deny to allow;
  - every one is a heredoc written to a file (or an interpreter body) whose
    text mentions aptly or publish/task/api, in the same call as a
    non-reader command;
  - work-around: write the file with the Write tool, or in a separate call.

## Correct layer

`_classify_body` (TEXT decision) and `_levels`, which computes the whole-call
facts once and passes them in. The scanner, the aptly rules, the legacy floor
and `settings.json` are unchanged.

## Tests

- DENIED gets every form both Design Challenger rounds reported for this
  class, including the process-substitution and hook-file forms.
- Every existing ALLOWED entry must still pass. Commands that were allowed
  before and are denied now are listed in logs/ from a replay of real
  commands in the transcripts, through `inspect()` only.
