# Phase 2: guard narrowing (rule A's trigger, interpreter code strings, `2>&1`)

Permission model phase 2. Kind: `tool`, SECURITY. Owner: the architecture
session, by May's GO of 2026-10-10 ("исправить конкретные проблемы разбора
команд и ложные срабатывания, не превращая guard в более сложную систему").
Architecture review row 2 (`README.md` section 3.2, classes B and C; section
5 row 2), May's decision 3 (relaxation after phase 5; P5 is merged, the
signer is not yet live, so the condition of row 2 applies: a form that (a) or
(b) would open and that reaches a publication stays denied).

## 1. The three defects

**(a) Rule A's trigger is the whole level.** `_aptly_rules` denies the
words `publish`, `task`, `api` in any exposed group when *any* expansion
(`$x`, `$(…)`, a glob, a brace) occurs anywhere in the level. The rule
exists for a command word built by expansion (`${a}ly publish`, -058 round
3). Argument expansions make it fire on data: `curl "$url/api/v4"`,
`python3 -c "d['publish']" "$f"`, `echo "publish hud $(date)"`,
`sed -i 's/a/task branch/' f; echo "$(date)"` (corpus RC3: records 4, 13, 15,
26, 31, 34, 43; -003 additional cases 1, 2, 5, 6, 9).

**(b) Interpreter code strings are commands.** `python3 -c CODE` (and
`perl|ruby|node|php -e/-c`) keeps CODE as one token of a runner group, so
every string literal in it is an aptly mention or a denied word
(`print('fake aptly')`, `d={'x':'publish record'}`, `'/srv/'+'aptly'+'/pool'`;
corpus RC2: records 3, 9, 19, 42 and the RC3 ones above; additional case 3).
A heredoc body in the same language is already a BLOB whose words count
only when it can start a process (`_STARTS_PROCESS`, -018).

**(c) `2>&1` reads as a write.** `_REDIRECT` tries `>>?` before `>&`, so
`2>&1` is the operator `>` with the target `&1`: a file write for
`_text_blockers` and `_is_reader`, which turned the P4 merge command (a
commit message with "publish" and a `$(…)`) into a rule-A denial (phase 3,
recorded for P2).

## 2. The changes (`.claude/hooks/command_guard.py`)

(a) `reach_expansion` becomes: a forced blob exists, **or** an exposed,
non-literal group *expands where a command may be built from it*
(`expands_where_it_runs`): some token of the group expands (`$`, a
substitution marker, `*`, `?`, `[`, a brace pattern) and either the group
runs something (a non-reader: its command word or any argument, so
`${a}ly publish`, `sh -c "${a}ly …"`, `eval`, `xargs`, `timeout`,
`fakeroot`, `eatmydata`, any wrapper known or unknown), or the group is a
reader whose output reaches a program that may run it: its pipeline
reaches any non-reader except an interpreter that already has its program
(a `-c`/`-e` code string, or a script operand) and names no stdin
(`-`, `/dev/stdin`, `/dev/fd/0`, `/proc/self/fd/0`) anywhere
(`_takes_data`); or a
redirect target of the group is a file a runner names (the test
`_exposed` already applies); or the group is a substitution consumed by an
exposed command. Today the trigger is the level's flag: an expansion in a
reader that feeds nothing (`echo "$(date)"`), or in a reader that feeds a
program taking data (`curl "$url/api/v4" | python3 -c …`, `| jq`,
`| python3 parse.py`), counts for a runner elsewhere; afterwards those do
not count, while `echo "${a}ly publish list" | sh`, `| timeout 60 bash`,
`| source /dev/stdin`, `| busybox sh`, `| make -f -`, `| python3
/dev/stdin`, `| some-unknown-tool`, `> /tmp/s.sh; bash /tmp/s.sh` all keep
denying. The level's `expansion` flag (set only by unquoted expansions)
still gates the check, so a single-quoted `'$x'` counts only when the
level really expands somewhere (an over-approximation that denies, never
allows). Everything else in rule A is unchanged: literal `aptly` anywhere
in reach still denies; the copy rule, rule E and the forced blobs are
untouched. There is no list of programs: every non-reader counts, and the
only carve-out is the interpreter whose program is visible.

(b) In `_aptly_rules`, the `-c`/`-e` code string of an interpreter group
(`_INTERP_WORD`: `python[0-9.]*|perl|ruby|node|php`; the option found as in
phase 3's `_option_string`, clusters such as `-Bc` included) is taken out
of the group's tokens for the word and mention tests, and added to the
blobs exactly when a heredoc body would be: `_STARTS_PROCESS` matches
(Ruby's `%x(…)` added, D3), or a backtick in `perl|ruby|php`, or the group
writes a file while another runner exists (the -018 "forced" rule): a
redirect target other than `/dev/null`, an unparsable one, **or a write
idiom in the code itself** (`open(…, 'w')`, `.write_text(`, `shutil.copy`,
`os.replace`, `File.write`, `writeFileSync`, …: `_CODE_WRITES`, after
phase 3's `_WRITE_IDIOMS`; D2). The group itself stays a runner (so the
other groups' exposure is unchanged). `python3 - <<EOF` bodies are
unchanged (already BLOBs).

(c) `_REDIRECT` tries the longer operators first: `(>&|>\||>>|>)`.
`_redirect_targets` already drops `>&N`; the phase-3 `_FD_DUP` filter in
rule 1 becomes redundant and stays.

Nothing else moves: the legacy floor and its fallback (phase 1), the
`_group_rules` (pkill -f, git add -A, rm -rf, force push, xwd), rules 1
and 3 (phase 3), the rehearsal and live allowances.

## 3. Must still deny

- Every form of the -058 round-3 list in `test_command_guard.py`: a literal
  `aptly` anywhere in reach; the expansion in the command word
  (`a=apt; ${a}ly publish list`, `$(printf apt)ly publish list`,
  `/usr/bin/apt?y publish list`, `{apt,-architectures=}ly publish drop`,
  `$'\x61ptly' publish list`); executed heredocs; copies of the binary.
- Runners with an expanding argument: `sh -c "${a}ly publish x"`,
  `bash -c "$cmd"` with `publish` in the level, `eval "${a}ly publish"`,
  `xargs ${a}ly publish`, `timeout 5 ${a}ly publish`, `ssh target "$x publish"`,
  `find . -exec ${a}ly publish \;`, `awk 'BEGIN{system("'${a}'ly publish")}'`,
  `fakeroot ${a}ly publish list`, `eatmydata`, `taskset -c 0`, `runuser`,
  `chrt`, `setpriv`, `sg -c`, `rlwrap`, an unknown wrapper; a reader with an
  expansion piped into a program that executes its stdin (`echo "${a}ly
  publish list" | sh`, `| bash -s`, `| sudo -s`, `| ssh target`, `| xargs
  -I{} {} publish list`, `| tee /tmp/l | sh`, `echo "…os.system('${a}ly
  publish list')" | python3 -`); a runner with the word and an expanding
  argument (`python3 t.py --note "publish $(date)"`, denied today, stays
  denied); substitutions in a runner's arguments (`python3 t.py $(printf
  publish) $(printf apt)ly`).
- Interpreter code that starts a process: `python3 -c "import os;
  os.system('aptly publish list')"`, `python3 -c "import subprocess; …"`,
  `perl -e 'print \`aptly publish list\`'`, `ruby -e '%x(aptly publish list)'`,
  `python3 -c "exec(…)"`, and a code string written to a file that a later
  runner runs, by a redirect (`python3 -c "print('aptly publish list')" >
  s.sh; bash s.sh`) or in the language (`python3 -c "open('s.sh','w')
  .write('aptly publish list')"; bash s.sh`, `Path(…).write_text`,
  `File.write`, `writeFileSync`).
- The whole -018 data file and every DENIED entry of the suite except the
  ones section 4 moves to ALLOWED with their class.

## 4. Newly allowed, by class (the replay must show nothing else)

- Class A (argument expansion): corpus records 4, 13, 15, 26, 31, 34, 43;
  additional cases 1, 2, 5, 6, 9; `curl "…/api/v4/$P" | python3 -c …`,
  `| jq`, `| grep`; a reader's expansion piped into a program that takes
  data (`cat "$f" | python3 t.py publish`).
- Class B (interpreter data strings): corpus records 3, 9, 19, 42;
  additional case 3; `python3 -c "print('aptly freeze')"`.
- Class C (`2>&1`): the P4 merge command shape (`git merge … -m "… publish
  …" >/dev/null 2>&1 && … $(…)`).

Test data entries of the suite that belong to these classes move from
DENIED to ALLOWED with the class in their label; any other change is a
defect.

## 5. Verification

- The suite (every other DENIED/ALLOWED entry unchanged; the -018 file
  unchanged); new ALLOWED entries for the classes; new DENIED entries for
  section 3's shell-runner and interpreter forms.
- Transcript replay (`replay_guard.py`) against main: every deny->allow in
  classes A, B, C, enumerated in the record; 0 allow->deny.
- One Design Challenger round on this note with May's termination rule
  (proven blocking defects only), one Verifier round, both bounded.
- Fresh-session checklist: `python3 -c "print('aptly freeze')"` runs;
  `curl "https://gitlab.com/api/v4/projects/$P"` runs; `a=apt; ${a}ly
  publish list` and `sh -c "${a}ly publish list"` are refused.

## 6. Design Challenger round 1: REVISE, and the revision

Findings: **D1** (blocking) the argument-executing programs were a list
(`_ARG_RUNNERS`); `fakeroot ${a}ly publish list`, `eatmydata`, `taskset`,
`runuser`, `chrt`, `setpriv`, `sg -c`, `rlwrap` were outside it and would
have been allowed. Taken structurally: (a) now counts an expansion in any
token of a group that runs something, so every runner, listed or not,
keeps denying and the list is gone; a reader's expansion counts only when
its pipeline reaches a program that executes its stdin (the short
`_stdin_runner` set), which keeps `echo "${a}ly publish list" | sh` denied
and lets `curl "…/api/v4/$P" | python3 -c …` through (the URL cases). **D2** (blocking) a code string that writes a file in
its own language for a later runner (`open('s.sh','w')…; bash s.sh`) was
not forced into a blob. Taken: `_CODE_WRITES`. **D3** (should) Ruby's
`%x(…)`. Taken. **D4** (note) the `_REDIRECT` reorder is clean. Round 2 is
asked on this revision.

## 7. Design Challenger round 2: REVISE, and the revision

Round 2 found four regressions against main in the round-1 revision, all
from listing the stdin-executing programs: **R1** a reader's expansion
written to a file a runner then runs (`echo "${a}ly publish list" >
/tmp/s.sh; bash /tmp/s.sh`) was not counted (the walk followed pipes
only); **R2** stdin shells behind wrappers (`| timeout 60 bash`, `nohup`,
`nice`, `setsid`, `stdbuf`, `ionice`, `flock`, `unshare`, `strace`,
`fakeroot`, `eatmydata`, `systemd-run`); **R3** `| source /dev/stdin`,
`| . /dev/stdin`, `| busybox sh`, `| make -f -`; **R4** `| python3
/dev/stdin`, `| perl /dev/stdin`. Taken structurally, as the Challenger
proposed: the list is gone; a reader's expansion counts when its output
reaches any non-reader except an interpreter whose program is visible,
when it writes a file a runner names, or when it is a substitution an
exposed command consumes. Every round-2 string now matches main; the 24
allowed forms (the registered cases, `curl "…/api/v4/$P" | python3 -c`,
`| jq`, `| grep`, `| python3 parse.py`) stay allowed. Pre-existing on main
and unchanged (out of scope, recorded privately): `cmd="${a}ly publish
list"; echo "$cmd" | sh` and the process-substitution forms `bash <(…)`,
`| tee /tmp/s.sh; bash /tmp/s.sh`. Round 3 (final) asked on this
revision.

Round 3 (closing) found two one-liners in that carve-out, taken: **B1**
`perl`/`ruby` run a command without parentheses (`perl -ne 'system $_'`):
for those owners the code string is a blob on `system`/`exec`/`spawn`/
`popen`/`fork` as words, as it already was on a backtick; **B2** an option
value was read as the script operand (`python3 -W ignore -`, `perl -I
lib -`): a stdin name anywhere in the group means "may run it", and the
code option is a short cluster ending in `c`/`e`/`E` (`-Werror` is not
one). Pre-existing on main and unchanged (out of scope): `echo "${a}ly …"
> /tmp/f; cat /tmp/f | sh`, `… | install /dev/stdin /tmp/s.sh; sh
/tmp/s.sh`, `… | { read c; eval "$c"; }`. Intended class-A relaxations the
Challenger noted: `curl "…/api/v4/$P" | python3 -m json.tool` and `… |
python3 -u scripts/taskctl.py list`.

## 8. Out of scope (recorded, not changed)

Class F of the review: `ssh target 'command -v aptly'` (RC7),
`grep aptly f | awk …` (RC6), `timeout 60 aptly repo list`, `dpkg -L aptly`;
corpus record 30 (`/srv/aptly` inside a sed substitution script, a phase-1
tightening choice) and record 11 (a sed operand that must exist). The
phase-1 floor gaps (P3/P4/P5/P16b, B5/B6) and the private guard-gap note
stay for a separate tightening decision.

## 9. Implementation and measurement (branch `arch/permission-model-phase2`)

`.claude/hooks/command_guard.py`, inside `_aptly_rules` and two helpers:
`expands_where_it_runs` (the three routes of section 2 (a)), `_takes_data`
(the carve-out), `_code_string` (`-c`/`-e`/`-E` and clusters ending in
them), `_CODE_WRITES`, `_PERL_RUBY_RUN`, `%x` in `_STARTS_PROCESS`; the
`_REDIRECT` order. Nothing else in the guard moves.

Tests: `test_phase2_narrowing_cases` reads
`scripts/tests/data/command_guard_p2_cases.json`: 96 forms that must stay
denied (every Design Challenger string of rounds 1-3 and the review's
must-deny list) and 46 newly allowed forms by class (the -003 corpus
records 3, 4, 9, 13, 15, 19, 26, 31, 34, 42, 43; the -003 additional cases
1, 2, 3, 5, 6, 9; the P4 merge command; the URL and JSON-key shapes). The
-003 data file moves record 13 from DENIED to ALLOWED (class A); every
other existing DENIED and ALLOWED entry is unchanged, the -018 data file
is unchanged. Suite: 546 OK (1 skipped).

Transcript replay (11 548 distinct commands, main against the branch;
each deny->allow re-run through three guards with one change switched off
to attribute it): 22 deny->allow, all in the classes: B 16, A 2, A+B 2,
B+C 1, A+B+C 1 (the P4 merge command: any one change allows it); 0
allow->deny; 0 changed reasons.

Still denied, by decision (section 8): corpus records 10 (`ssh target
'command -v aptly'`), 11 and 30 (sed), 36 (`grep aptly | awk`).
