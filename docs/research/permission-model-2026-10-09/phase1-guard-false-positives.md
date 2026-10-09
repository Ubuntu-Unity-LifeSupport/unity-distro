# Phase 1 - command_guard false-positive defects (design; Design Challenger APPROVE at round 8, 2026-10-09)

Kind: `tool`, SECURITY-adjacent. Scope as May approved it on 2026-09-29
for UNITY-20260929-003 and confirmed on 2026-10-09 (decision 3): narrow
false positives only; fail-closed kept; every aptly rule kept; nothing
denied today becomes allowed except the enumerated forms below. B's card
(`b/UNITY-20260929-003`, `docs/research/UNITY-20260929-003-guard-false-positives/README.md`,
corpus of 44 refusals) is the input; this record supersedes its "Chosen
approach" where round 1 found defects.

## Invariant

Everything the guard denies today it keeps denying, except the four
enumerated classes. A call is allowed only when every command the shell can
run from the text has been seen and passed every rule. Text that is never
run (quoted heredoc bodies read as data, commit messages) is not tokenised
as shell. The guard stays fail-closed: a shell text that still does not lex
after the line-wise fallback of RC1, and a scanner error on the command
itself, still deny.

## Changes

### Step 0 - heredoc TEXT conditions: no new code

Round 1, finding 1 (FACT): the merged -018 `_text_blockers` already
implements the three conditions of B's step 0 (`compound`, `piped`,
`expands`) plus `forced`. `function f {` is not caught by `compound`, but
that group is not a reader, so the body is SCRIPT anyway. Nothing to do.

### RC1 - a legacy floor that never fails, run always

Today `_legacy_groups` lexes the whole text with shlex, heredoc bodies
included; an apostrophe in a quoted-delimiter body is "No closing quotation"
and the call is refused before the heredoc-aware scanner runs (13 corpus
records, C's recurring cases, this session's own case of 2026-10-09).

Change (B's original step 1, restored after round 2 finding 1): the
whole-text floor stays exactly as today. **Only when it fails to lex**, the
line-wise fallback runs instead of refusing:

1. backslash-newline continuations are joined;
2. the whole text is lexed twice with the guard's own `_lex` (newline
   separates groups; a double-quoted string may span lines, as in a Python
   docstring or a multi-line commit message): once with every apostrophe
   character removed, once with every apostrophe, double quote and
   backslash removed (round 5 finding 2: a `"` that was inside single
   quotes becomes active after the apostrophe removal and could swallow a
   separator together with a rule token, K12/K15);
3. a text that does not lex in at least one of the two forms is refused as
   today ("could not parse");
4. `_group_rules` is applied to every group of both lexings; a rule that
   trips in either denies;
5. on this fallback path only, the second lexing is also refused when it
   holds an `rm` group with `-r` and `-f` and no path operand, or a
   `pkill`/`pgrep` group with a lone `-` token (round 6 finding 2: a
   separator inside a double-quoted token under the `'"'` pairing hides
   from both lexings, K16, K18-K21; the `rm` members execute on a relative
   path that starts with the separator). Because this applies only where
   the whole-text floor already refuses, it is not a tightening beyond
   today (`dc6.py tight_inspect`: 16/16 records including record 5, 0
   changes on the 195 test commands);
6. on this fallback path only, in each of the two lexings, a group whose
   command is `rm` with `-r` and `-f`, `pkill`/`pgrep`, `git add` or
   `git push` is judged together with the **first token of the following
   group**, the token a quote-hidden separator orphaned (round 7 finding 1:
   `rm -rf /tmp/a ";$X/y"` executes a recursive forced removal on an
   unguarded variable and was allowed by step 5 because the rm group had a
   path): an unguarded variable or glob after `rm -rf`, a lone `-` or an
   `-f`-like token after `pkill`/`pgrep`, a broad operand (`-A`, `--all`,
   `.`, `docs`, `docs/`) after `git add`, a force token after `git push`
   each deny (`dc8b.py nb_inspect`: 16/16 records, 0 changes on the 195
   test commands, R1-R7, G2, G4, P2, P6, K1 denied, no allow->deny).
   An order-free variant that judged every token of the text against every
   rule command (`dc8.py soup_inspect`) covered only 12 of 16 records and
   was rejected.

Round 3 (X1, X2, X7) showed that splitting a non-lexing line on whitespace
with all quotes removed would allow forms that the whole-text floor denies
when no apostrophe is present; round 4 showed that a line-wise lexing
covers only 6 of the 13 RC1 records, because the others carry a
double-quoted string that spans lines (`dc4.py`). The whole-text lexing
after apostrophe removal covers all 16 RC1/RC1b parse-error records, keeps
X1, X2, X7, Z1a-Z4a, P20, P26 and A1-A3 denied, and changes none of the
195 test commands (`dc4d.py`). Plain `_legacy_groups` on the stripped text
would be wrong (newline is whitespace there). With the two lexings the
fallback can create a denial a no-apostrophe sibling does not have (an
accepted RC1 false positive) but hides none of the probe sets' rule
tokens (`dc5c.py`: 16/16 records, 0 changes on the 195 test commands,
K1-K3, K12, K15 denied). `git add '-A '` becomes allowed, as its sibling
is. X3 (`echo $'abc` in a bash body) turns from refused into allowed; it
is a bash syntax error and is recorded.

**No residual in this class (rounds 5-6).** K16 (the `'"'` pairing of K12
with X7's option split across lines) was first taken as a residual because
the refusal that closed it lost corpus record 5. Round 6 showed the class
has executable members (K18 `rm -rf "<newline>$X/y"`, K19 `rm -rf ";$X/y"`)
and a refusal that costs nothing (step 5 above). The pre-existing
backslash variants K4-K7/K13/K14 (allowed on main today) and the quoted
separator forms Q1-Q3 (`rm -rf ';' $X/y`, allowed on main today, a
pre-existing gap outside this phase) go to the private gap note.

**SCRIPT bodies that fail to scan** (round 3 finding 2): today a SCRIPT
heredoc body whose own scan raises `ScanError` becomes a blob, and
`_aptly_rules` returns at "no runners" before looking at blob words; such a
call is denied only by the whole-text floor's refusal. Once that refusal
turns into a decision, the blob must be checked: a `ScanError` blob made
from a SCRIPT body carries `forced=True` **only when the whole-text floor
failed and the fallback decided** (round 4 finding 2: forcing it
unconditionally would deny today-allowed forms B11-B16, where a quoted body
fails the scanner on a lone backtick next to an outer expansion). On the
fallback path the forced blob's words are checked without a runner (the
same path -018 uses for a body written into a file git may run). This keeps
Z1a (`git commit -F - -e` with an apostrophe line and a publish line) and
Z2a (`-a`) denied, as their no-apostrophe siblings are, and changes nothing
on the 195 test commands.

Round 1 had proposed running the line-wise floor always; round 2 showed
(B1-B7) that this would deny text bodies that are allowed today (a doc
file or a commit message containing a `pkill -f` or `git add -A` line) and
two existing ALLOWED tests. That proposal is withdrawn. The fallback can
only turn today's refusal into a decision, never change a decision the
whole-text floor makes. The heredoc-aware scanner then runs unchanged for
the aptly rules; a `ScanError` there is still "could not parse".
Pre-existing gaps of the floor (P3 multi-line quoted path, P4 ANSI-C
`$'-A'`, P5 backslash-continued `git add -A`, P16b; B5/B6 bodies run by
`bash`/`sh` with a `pkill -f` or `git add -A` line) are recorded as out of
scope: closing them is a tightening that needs its own decision (candidate
for phase 2 or 6, with May's OK).

### RC1b - `git commit -F -` bodies are TEXT

Round 2 finding 2: once RC1 no longer refuses apostrophe bodies, the three
RC1b corpus records (6, 24, 35) are already allowed, because a body that
hits `ScanError` in `_levels` becomes a harmless blob. RC1b's remaining
class is a message that lexes and contains a line starting with `aptly`
(or the words with an expansion) and is therefore scanned as SCRIPT today.
`git tag -F -` is dropped: it needs a tagname operand, which the operand
list below forbids, so that branch would be unreachable.

A body owned by `git commit` reading its message from stdin is TEXT under
the -018 conditions and today's TEXT conditions, with these precise rules
(round 1 finding 3):

- the subcommand is found after git's global options (`-C dir`, `-c k=v`
  with `k` in `_GIT_SAFE_CONFIG`, `--git-dir=`, `--work-tree=`), with the
  same walker `_is_reader` uses, not at `group[1:3]`;
- the message option is exactly `-F -`, `-F-`, `--file=-` or `--file -`;
- the only other operands allowed are `-q`, `--quiet`, `-s`, `--signoff`,
  `--no-verify`, `--amend`, `--allow-empty`, `--author=...`,
  `--date=...`, `-m`-less pathspecs after `--`; anything else (`-e`,
  `--edit`, `-t`, `--template`, `-c`/`-C` reuse, `-a`, an env prefix, a
  `-c core.editor=...`) keeps the body SCRIPT as today;
- an unquoted body still has its `$(...)` and backticks collected (P11
  stays denied); `--author=`/`--date=` values with a substitution are
  denied today through substitution collection and stay so (C1, C1b);
- P13b (a `-F -` message body with an `aptly publish` line) is **allowed**
  under this form; today it is denied by the aptly rules on the SCRIPT
  body. It is the enumerated RC1b form, stated explicitly (round 2
  finding 3).

### RC4 - `sed` substitutions as a reader

`sed` is also a reader when all of these hold:

- each argument is an exact option among `-n -E -r -i -s -z -u` (no
  combined short options, no `-i.bak`, `--in-place=`, `-e`, `-f`,
  `--expression`, `--debug`), an existing regular file, or one
  substitution script;
- the script fully matches
  `s<d>((?:\\.|[^\\\n<d>])*)<d>((?:\\.|[^\\\n<d>])*)<d>[gIip0-9]*` with a
  one-character delimiter that is not alphanumeric, backslash, newline or
  whitespace;
- the script contains neither an aptly occurrence nor `publish`/`task`/
  `api` (so `sed -i` writes that `_exposed` does not follow cannot smuggle
  them);
- **no operand is the aptly binary by file identity** (finding 4, P8:
  `sed -i 's/a/b/' /usr/bin/aptly` is denied today and must stay denied;
  `_same_as_aptly(a, aptly, False)` on every operand, as line 580 does for
  redirect targets).

Corpus record 13 (`s/a/task branch/` next to `$(date)`) is **not** covered:
its script contains `task`. It stays denied as an accepted false positive
until phase 2 (finding 4, correcting B's card).

### RC5 - `/srv/aptly` inside a token

`_is_aptly` removes the text `/srv/aptly` before its tests only when:

- it is preceded by the token start, `=`, `:`, a quote or `,`, and followed
  by the end, `/`, `|`, `:`, a quote, a space, `,` or `;)]`;
- **the token belongs to a group that is not exposed** (finding 5, a real
  regression otherwise: P6, P7, P7b are `bash -c '...'` or reader-output
  piped into `sh` where the stripped text was the sole mention and the
  shell inside reassembles the binary name). Exposed groups (runners, and
  readers whose output reaches a runner, as `_exposed` computes) keep
  today's behaviour.

Only the matched text is removed, never the whole token, never from a
command word; `_same_as_aptly` still runs. Corpus record 30 (`sed` output
run by `bash`) therefore stays denied as an accepted false positive.

## Correct layer

`command_guard.py`: `inspect` (floor order), `_legacy_groups` (line-wise
fallback), `_classify_body` (RC1b), `_is_reader` (RC4), `_is_aptly` plus a
group-exposure argument (RC5). `settings.json` and the fail-closed wrapper
untouched.

## Tests (`scripts/tests/test_command_guard.py`, data as JSON written with the Write tool)

- ALLOWED: the minimal forms of the 17 corpus records: RC1 (13), RC1b
  (3: records 6, 24, 35) and RC4 (1: record 11; record 13 stays denied),
  none for RC5 (record 30 stays denied),
  plus `git -c user.name=x commit -F -` with an apostrophe body (P19),
  `git commit -F - -q -s` with an apostrophe body, P13b, an RC4 case on a
  file that exists at test time (tempdir path). The RC2, RC6 and RC7
  records (12) stay denied and are not in this list (round 2 finding 4).
- DENIED (from the probe sets `probes.json`, `probes2.json` and round 3's
  transforms, stored as test data): P6, P7, P7b, P8, P8b, P9, P11, P12,
  P12b, P12c, P14, P15, P21, P24, P25, P26, C1, C1b, D1, D4, X1, X2, X7,
  Z1a, Z2a, Z3a, Z4a; a `bash <<'EOF'` body with
  `rm -rf $X/y` after an apostrophe line; `cat <<'EOF' | sh` with a publish
  line; `sed 's/x/.../e'`, `sed -e`, `sed 's/a/b/w f'` with aptly;
  `/srv/aptly/bin/aptly publish list`; a heredoc body plus `git add -A` or
  `rm -rf $X` in the same call.
- Every existing DENIED and ALLOWED entry and the -018 data file
  unchanged (B1-B7 and the two ALLOWED tests round 2 named stay allowed).
- Replay of all distinct transcript commands through `inspect()` of main
  and of the branch (`replay_guard.py`, validated main-vs-main on 11139
  commands with 0 differences): every deny->allow change belongs to
  RC1/RC1b/RC4/RC5; **0 allow->deny changes**.

## Acceptance (fresh A, B, C sessions)

The permission-freeze checklist; a quoted-delimiter heredoc with an
apostrophe in the body is allowed; `pgrep -f`, `git add -A`, `rm -rf $X/`,
`aptly publish list` denied.

## Rollback

`baseline-20261009/command_guard.py` or `git checkout <merge base> --
.claude/hooks/command_guard.py`; `install_command_guard.py --check`.

## Design review round 1 (2026-10-09): REVISE - findings taken

1 step 0 already in -018 (no code); 2 line-wise floor always, P5 closed,
pre-existing gaps recorded; 3 RC1b operands and subcommand walker spelled
out; 4 RC4 operand identity check, record 13 excluded; 5 RC5 only in
non-exposed groups, record 30 stays denied; 6 the test additions.

## Design review round 2 (2026-10-09): REVISE, taken

1 (blocking) the always-on floor is withdrawn: it would deny text bodies
allowed today (B1-B7) and two existing ALLOWED tests; the fallback runs
only when the whole text fails to lex, as B designed it; P5/B5/B6 recorded
as pre-existing gaps out of scope. 2 RC1b narrowed to its real class (a
lexable message with a line that starts with the binary's name); `git tag`
dropped. 3 P13b named as allowed under RC1b. 4 test arithmetic: 17 records
allowed, 12 stay denied. 5 and 6 confirmed, no change. Pre-existing gaps the
Challenger found are kept in a private note (not for the public repository)
for a later tightening decision.

## Design review round 3 (2026-10-09): REVISE, taken

1 (blocking) fallback step 3 no longer splits a non-lexing line with all
quotes removed: it removes apostrophes only and refuses a line that still
does not lex, so X1/X2/X7 stay denied as their no-apostrophe siblings are.
2 (blocking) a `ScanError` blob made from a SCRIPT body is `forced`, so its
words are checked without a runner; Z1a/Z2a stay denied. 3 the invariant
sentence names the two refusals that remain; record counts spelled out
(13 + 3 + 1 = 17). 4 confirmed. 5 noted: `-F /dev/stdin` and
`git tag -F - v1` become allowed through the RC1 route (an apostrophe body
that lexes after step 3 is TEXT only under the RC1b rules; otherwise it is
scanned as today); `-- pathspec` and `-c commit.gpgsign` are RC1b operands
and are TEXT under its rules (round 4 finding 3). Remark taken: the surviving
asymmetry (a prose line that starts with the binary's name or `pkill -f`
inside an apostrophe body is denied by the per-line floor, while the same
body without an apostrophe is allowed) is an accepted RC1 false positive.

## Design review round 4 (2026-10-09): REVISE, taken

1 (blocking) step 3 is the whole-text `_lex` after apostrophe removal, not
a line-wise lexing: 16/16 parse-error records covered, every probe set
unchanged (`dc4d.py`); the ALLOWED tests use the full corpus texts, not
only the minimal forms. 2 (blocking) the forced ScanError blob only on the
fallback path. 3 finding-5 wording corrected. 4-5 confirmed. 6 X3
recorded.

## Design review round 5 (2026-10-09): REVISE, taken

1 confirmed. 2 (blocking) the monotonicity claim was false (an active `"`
after apostrophe removal, K12/K15): the fallback now lexes twice (without
apostrophes; without apostrophes, double quotes and backslashes) and a rule
tripping in either lexing denies, the remedy round 5 verified (`dc5c.py`).
3 taken as 2. 4 K16 first recorded as an accepted residual rather than
losing corpus record 5 (superseded in round 6). 5 confirmed. 6 the
backslash variants go to the private gap note.

## Design review round 6 (2026-10-09): REVISE, taken

1 confirmed. 2 (blocking) the K16 class has executable members (K18, K19,
K19g); the residual is withdrawn. 3 the verified zero-cost refusal on the
fallback path (step 5) closes K16 and K18-K21 with 16/16 records and 0
test changes. 4 superseded by 3. 5 confirmed. Remarks: "in at least one
form" wording; Q1-Q3 (quoted separator as a group boundary, allowed on main
today) recorded in the private gap note as a pre-existing gap for a
separate tightening decision.

## Design review round 7 (2026-10-09): REVISE, taken

1 (blocking) the R class: `rm -rf` with a benign path plus a quote-hidden
separator orphaning an unguarded operand executed and was allowed under
step 5. Step 6 (the neighbour rule, measured by the architecture session
in `dc8b.py`) closes R1-R7 and the analogous G2, G4, P2, P6, K1 with
16/16 records and 0 test changes. Deny->allow outside the enumerated
RC1/RC1b forms stays limited to X3 (bash syntax error), K22 (`git add`
with the option split across lines: stages a file literally named so, not
a broad staging) and A4 (`"apt;ly" publish`: a nonexistent command), each
recorded.

## Implementation (branch `arch/permission-model-phase1`)

`.claude/hooks/command_guard.py`:

- **RC1.** `inspect()` keeps the whole-text floor; when it cannot lex the
  text, `_fallback_floor()` decides: continuations joined, two lexings with
  the guard's own `_lex` (apostrophes removed; apostrophes, double quotes
  and backslashes removed), refusal when either does not lex,
  `_group_rules` on both, then `_fallback_refusals()` (step 5: `rm -rf`
  without a path or `pkill`/`pgrep` with a lone dash in the second lexing;
  step 6: `rm -rf`, `pkill`/`pgrep`, `git add`, `git push` judged with the
  first token of the following group). `_levels(command, fallback=True)`
  makes a SCRIPT body that fails to scan a forced blob on that path only.
- **RC1b.** `_git_commit_stdin_message()`: `git commit` reading its message
  from stdin (`-F -`, `-F-`, `--file=-`, `--file -`) with only `-q`,
  `--quiet`, `-s`, `--signoff`, `--no-verify`, `--amend`, `--allow-empty`,
  `--author=`, `--date=` and pathspecs after `--`, global options walked as
  `_is_reader` does; `_classify_body` returns TEXT for it under the -018
  conditions.
- **RC4.** `_is_reader` accepts `sed` with exact options `-n -E -r -i -s
  -z -u --quiet`, printing scripts and at most one substitution script
  (`_SED_SUBST`, flags g/I/i/p/number only) that carries neither the text
  `aptly` nor publish/task/api, on operands that are existing regular files
  and not the aptly binary by inode.
- **RC5** as narrowed in round 1 (strip `/srv/aptly` only in groups that
  are not exposed) changes no verdict: a token in a non-exposed group is
  never a mention, and the early gate already passes such commands when
  runners are elsewhere. No code; corpus record 30 stays denied as the
  accepted false positive.

Tests (`scripts/tests/test_command_guard.py`, data
`scripts/tests/data/command_guard_003_cases.json`): the Design Challenger
probes of rounds 1-8 (synthetic, 229 strings) with their verdict under the
new guard, generated with a check that every deny->allow change against
main is an enumerated RC1/RC1b form or one of X3, K22, A4 and that no
allow->deny exists; the corpus RC1/RC1b minimal forms (16); explicit RC1,
RC1b and RC4 cases. The data file holds no corpus full text (several corpus
records carry private coordinator notes); the full texts were replayed
privately (below).

Measurements before the merge (`dc_impl_check.py`, `replay_guard.py`):

- the implementation agrees with the round-8-approved simulation on every
  probe except P13b, which RC1b allows by design;
- corpus: 16 of 16 RC1/RC1b records allowed, the 10 true positives and the
  14 other false positives (RC2/RC3/RC5/RC6/RC7) still denied, record 11
  (RC4) still denied because its `cd` makes the sed operand unresolvable
  from the hook's working directory;
- the 195 commands of the existing test lists and the -018 data file:
  0 verdict changes;
- replay of every distinct transcript command (11216): 0 allow->deny;
  257 deny->allow, of which 254 were "could not parse" refusals (RC1) and 3
  were `git commit -q -F -` messages denied as aptly mentions (RC1b).
