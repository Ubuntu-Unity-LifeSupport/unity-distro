# UNITY-20260928-012 - wire command_guard into every agent session

```yaml
task_id: UNITY-20260928-012
task_kind: tool
package: unity-distro .claude/hooks/command_guard.py wiring (Claude Code PreToolUse hook)
target_series: resolute
issue: command_guard.py is not loaded in agent sessions rooted at /home/claude
status: REPRODUCED
issue_search_result: NOT_FOUND
source_version: main 9d8db2e
binary_version: not_applicable
source_commit: 9d8db2e
observed: see Reproduction
expected: every Bash/Monitor call of every Claude Code session of user claude on builder passes through command_guard.py, whatever the session cwd; a guard that cannot run blocks the call
existing_fix_result: NOT_FIXED
architectural_task: false
design_challenger_required: true
design_review_result: APPROVE  # round 1 REVISE, round 2 APPROVE (2026-09-29)
```

## Reproduction

FACT (2026-09-29, sessions A a9056178, B b7902aab, C a2de0c56; recorded by C in
`~/coordinator/PENDING-MAY.md`, section 2026-09-29): the harmless probe
`pgrep -f unity-guard-probe-zzz` ran in all three sessions (`probe rc=0`, the
match is pgrep's own shell). `CLAUDE_PROJECT_DIR` is unset in the Bash
environment; `$PWD` is `/home/claude/unity-distro`.

FACT (B, this session): the same command fed to the guard directly is denied:

```
$ python3 .claude/hooks/command_guard.py < probe.json   # tool_input.command = the probe
Pattern-based process matching is blocked; identify the exact PID.
guard rc=2
```

So the guard would deny the probe; the probe ran, therefore the guard was not
invoked. Existing guard suite on main: `31 passed, 265 subtests passed`.

FACT (config at 9d8db2e): the only hook definition is
`unity-distro/.claude/settings.json`, PreToolUse `Bash|Monitor`,
`python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/command_guard.py"`.
`~/.claude/settings.json` has no `hooks` key. `~/.claude/hooks` does not exist.

## Root cause

`root_cause_mechanism`: project settings (`<project>/.claude/settings.json`)
are loaded only for sessions whose project root is that directory. May starts
the agent sessions with the project root `/home/claude` (the Claude Code project
directory key is `-home-claude`); `/home/claude/.claude/settings.json` there is
the *user* settings file and has no hooks. `cd unity-distro` inside a session
does not change the project root, so the unity-distro project hook is never
read. Nothing reports its absence.

INFERENCE: every session since the hook was written (UNITY-20260927-058/-057)
that was not started inside `~/unity-distro` ran without it. The memory note
`unity-distro-guard-scope` already said so.

## Invariant

1. Every PreToolUse `Bash` or `Monitor` call of any Claude Code session of user
   `claude` on builder, in any cwd, including subagents, runs the current
   `command_guard.py` from `main`, exactly once.
2. If the guard cannot run or does not answer (missing file, interpreter,
   import error, crash), the call is blocked with a visible reason - never
   silently allowed.
3. The guard's decisions are unchanged (this task changes wiring, not rules).

4. Only the guard's exit status decides: nothing the guard process prints on
   stdout reaches Claude Code (JSON there would override the exit code).

## Claude Code hook semantics (code.claude.com/docs/en/hooks.md, fetched 2026-09-29)

- FACT: exit 2 blocks and shows stderr; exit 0 = no objection. "Any other exit
  code doesn't block on its own ... the action proceeds". A plain
  `python3 /path/guard.py` therefore fails open on a missing interpreter (127)
  or a crash before `main()` (1). A missing script file gives 2 (measured).
- FACT: "With a parsed object that passes schema validation ... Claude Code
  ignores the exit code and the JSON alone decides the outcome ... including
  `permissionDecision`." Anything that makes the guard's stdout valid JSON
  (e.g. a shadowed module) decides on its own.
- FACT: "A timed-out `command` ... hook doesn't block the tool call." Default
  timeout 600 s, field in seconds. A hung guard fails open unless something
  inside the hook turns the hang into exit 2 first.
- FACT: command hooks run under `sh -c`.
- FACT: "If you define the same handler in more than one settings file, it
  runs once." "All matching hooks run in parallel." Different command strings
  in user and project settings both run.
- FACT: `${CLAUDE_PROJECT_DIR}` is "the project root where the session
  started" - for these sessions `/home/claude`, i.e. the project hook's path
  resolves into whatever tree the session is rooted in.
- FACT: the file watcher applies hook edits to already running sessions, so
  installing changes A's and C's live sessions at once.
- FACT: `disableAllHooks` exists; project settings can override user settings.

## Design (approach A, revised after Design Challenger round 1: REVISE)

One handler, byte-identical in `~/.claude/settings.json` (user, loaded by
every session of user `claude`, any cwd) and in
`unity-distro/.claude/settings.json` (project; deduplicated by Claude Code, and
still covers a session that does not load user settings):

```json
{"type": "command", "timeout": 30,
 "command": "/usr/bin/timeout -s KILL 20 /usr/bin/python3 -I /home/claude/unity-distro/.claude/hooks/command_guard.py >/dev/null || { rc=$?; [ \"$rc\" -eq 2 ] || echo \"command_guard did not decide (rc=$rc); tool call blocked.\" >&2; exit 2; }"}
```

matcher `Bash|Monitor`. Line by line:

- `/usr/bin/timeout -s KILL 20`: a guard still running after 20 s is killed
  well inside Claude Code's 30 s, so a hang becomes a block instead of a
  timeout pass (measured: rc 124; a guard killed by a signal: rc 15; a missing
  interpreter: rc 127 - all end in exit 2).
- `/usr/bin/python3 -I`: isolated mode ignores `PYTHON*` variables, the user
  site directory and the cwd on `sys.path`; the guard imports only the
  standard library.
- absolute path to the shared base checkout, which stays on `main`
  (TWO-AGENTS.md): 30 task branches carry older guards, and
  `${CLAUDE_PROJECT_DIR}` resolves into whichever tree a session is rooted in.
- `>/dev/null`: the guard writes decisions to stderr only; its stdout is
  discarded so it can never become a JSON decision (invariant 4).
- `|| { rc=$?; ... exit 2; }`: `$?` is the status of the pipeline to the left
  (inside `{}` still that status). Every non-zero status, including signals,
  exits 2; for rc 2 the guard already printed its reason, for any other the
  hook prints "command_guard did not decide (rc=N)". Exit 0 only when the guard
  returned 0. The `"` inside are JSON-escaped in the settings file; tests run
  the command parsed from the written file, not a retyped copy.

`scripts/install_command_guard.py`:

- `--check` (read-only; exit 1 with the reason): the handler is present exactly
  once and byte-identical in both files; no other Bash hook shadows it;
  `disableAllHooks` is not set; the base checkout has `HEAD` = `refs/heads/main`,
  `command_guard.py` has no uncommitted change (`git diff --quiet HEAD --`),
  and it reports how far local `main` is behind `origin/main` (no fetch).
- `--diff`: prints the unified diff `--apply` would make to
  `~/.claude/settings.json`; `--apply` writes it (keeps every other key,
  idempotent, replaces a stale guard handler, refuses unparseable JSON, writes
  atomically, keeps a backup `settings.json.bak-UNITY-20260928-012`).

Updating the deployed guard: a guard change reaches sessions when it is merged
to `main` and the base checkout is pulled (`git -C ~/unity-distro pull
--rebase`, the existing base-update step). Until then `--check` reports
"behind origin/main".

Who runs `--check`: every agent at session start, right after registering
(added to TWO-AGENTS.md next to the registry step), together with the
`pgrep -f` probe, which must be denied.

Rollback (a broken handler blocks every Bash in every live session at once):
remove the handler with the Edit tool (not matched by the hook) or restore
the backup with Write; May sees the diff before `--apply`.

Rejected alternatives:

- B. Project hook only, sessions started in `~/unity-distro`: May starts them
  in `/home/claude`; any cwd is required; nothing enforces the start directory.
- C. Copy of the guard in `~/.claude/hooks/`: drifts from `main` after every
  guard change.
- Removing the project entry: not needed for single execution (dedup) and
  loses coverage for sessions without user settings.
- D. Managed settings in `/etc/claude-code/`: root writes, belongs to
  UNITY-20260928-001.

## Known limits (not fixed here)

- Agents can still edit `~/.claude/settings.json` or set `disableAllHooks`
  (write access, sudo) - UNITY-20260928-001.
- A session rooted in an old task worktree whose project settings still carry
  the old `${CLAUDE_PROJECT_DIR}` handler runs two different guards in
  parallel; the old one can only add denials (it may lack the rehearsal
  allowance), until that branch is rebased or merged.
- A non-dict hook payload raises `AttributeError` in the guard's `main()`
  (rc 1); the wrapper turns it into a block. The guard itself is not changed
  (invariant 3).
- A SIGKILL from the inner timeout that lands after `_log_rehearsal` wrote
  its line but before exit 0 blocks a command that is already logged
  (Design Challenger round 2). Unlikely: the guard normally runs in well under
  a second.
- Worst-case guard time on a rehearsal root near `REHEARSAL_MAX_ENTRIES` is
  not measured: `/var/tmp/aptly-rehearsal` is out of bounds for this task. If
  a legitimate rehearsal approaches 20 s, raise the inner timeout, keeping it
  below the hook timeout.
- `--check`'s "behind origin/main" count reflects the last fetch only.
- `--check` does not read `settings.local.json`, managed settings or a
  project-level `disableAllHooks` (Verifier round 1 remark).
- The guard remains a pattern safety net, not a security boundary.

## Validation plan

Regression tests (`scripts/tests/test_install_command_guard.py`), run on tmp
copies, never on the real `~/.claude/settings.json`; the handler command is
taken from the written file and run with `sh -c`, with the guard path
substituted by a test copy or stub:

- probe payload: rc 2 + guard message; harmless command: rc 0;
- guard path missing; interpreter missing; stub raising at import; stub that
  sleeps past the inner timeout; non-dict payload: rc 2 + reason. Before the
  change (plain `python3 path`) the interpreter, import, sleep and non-dict
  cases pass the call;
- hostile `PYTHONPATH` module shadowing `json` that prints an allow JSON and
  exits 0: still rc 2 on the probe, empty stdout;
- installer: keeps other keys, idempotent, replaces a stale entry, refuses bad
  JSON, backup written; `--check` detects missing, duplicated, altered,
  project/user mismatch, `disableAllHooks`, base not on main, dirty guard.

Live proof in a NEW session started by May (root `/home/claude`), harmless
probes only (no aptly publish, `/srv/aptly` and `/var/tmp/aptly-rehearsal`
untouched):

1. no marker: denied (probe `pgrep -f unity-guard-probe-zzz`; rehearsal path
   without marker - form agreed with C);
2. with marker: allowed - only after C writes the marker on May's GO,
   coordinated separately;
3. the live form is denied;
4. logging: exactly one rehearsal-log line per allowed command;
5. a subagent's Bash call is guarded; a hang is simulated only on a test stub,
   never on the live handler;
6. guard runs once per call in a session rooted in `~/unity-distro`
   (execve count of `command_guard.py`, e.g. bpftrace on builder).

## Validation record

Implementation: branch `b/UNITY-20260928-012`, commit 379f98f (on 9d8db2e).

- Regression tests, unmodified wiring (`.claude/settings.json` at 9d8db2e):
  `logs/01-tests-before.txt` - 9 of 25 fail: crash at import (rc 1 passes the
  call), interpreter missing (127), hang (no inner timeout), signal, non-dict
  payload, hostile `PYTHONPATH` (rc 0 with an allow JSON on stdout), stdout
  JSON, and the two project-settings checks.
- After: `logs/02-tests-after.txt` 29/29 (25 at 379f98f, 4 added after
  Verifier round 1 remarks); full suite `logs/03-full-suite.txt` 134/134 (`python3 -m unittest discover -s scripts/tests`).
- Installed 2026-09-29 08:09Z by `install_command_guard.py --apply` after May
  approved the `--diff` output in session b7902aab; backup
  `~/.claude/settings.json.bak-UNITY-20260928-012` (sha256 in
  `logs/04-installed-state.txt`).
- In the already running session b7902aab (hot reload; NOT the required
  new-session proof): the probe `pgrep -f unity-guard-probe-zzz` was denied by
  the hook ("PreToolUse:Bash hook error: [...] Pattern-based process matching
  is blocked"); ordinary commands pass. A heredoc with backticks in one of
  B's own commands was denied ("could not parse shell quoting") - the guard's
  existing fail-closed parse rule, now active in this session.
- Probe verdicts of the installed handler, fed as payloads (never executed):
  `logs/04-installed-state.txt`. The live-form probes use a non-existent
  binary named `aptly` (`/nonexistent/aptly ...`), so they are harmless even if
  a hook failed; `echo`/`:` forms are allowed by design (UNITY-20260927-058:
  mentions in reader-only commands).
- `--check` reports NOT OK until merge only because the base checkout's
  project settings still carry the old handler (expected; see Known limits:
  until then a session rooted in `~/unity-distro` runs two handlers).

## New-session proof (pending; May starts the session, C coordinates)

After the merge to `main` (so `--check` is OK and the project handler is
identical), in a NEW session rooted at `/home/claude`, results into
`logs/05-new-session.txt`:

1. `python3 ~/unity-distro/scripts/install_command_guard.py --check` - OK.
2. No marker, denied: probe P1 as a real Bash call - hook denies.
3. Live form denied: P3 and P3b (`logs/probes.json`) as real Bash calls -
   hook denies (harmless if executed: the binary does not exist).
4. Harmless commands pass: P4-P6.
5. A subagent runs P1 - hook denies.
6. Run count: in a session rooted in `~/unity-distro`, one `command_guard.py`
   execve per Bash call (bpftrace on builder).
7. Marker allows / exactly one rehearsal-log line: needs C's marker after
   May's GO and runs the rehearsal command itself (-047 R territory);
   coordinated with C separately, not run by this task on its own.
