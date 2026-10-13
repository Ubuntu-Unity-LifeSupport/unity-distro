# UNITY-20260928-012 - independent verification

## Round 1 (2026-09-29, ephemeral Verifier subagent, branch tip 9b2c4f0)

Verdict: **INCOMPLETE**, `REVIEWED`. No FIX_INVALID, FIX_PARTIAL,
TEST_INVALID, ROOT_CAUSE_UNPROVEN or PATCH_TOO_BROAD finding.

Checked by the Verifier:

- `test_install_command_guard.py` 25/25, full suite 130/130 in the worktree;
  the before-run reproduced independently (tree of 9b2c4f0 with the 9d8db2e
  `.claude/settings.json`): the same 9 failures as `logs/01-tests-before.txt`.
- No path where the handler exits 0 without the guard's own exit 0; missing
  binary, crash, signal, inner KILL timeout all end in exit 2; stdout cannot
  reach Claude Code; `-I` blocks a hostile `PYTHONPATH`.
- Installer in a tmp tree: other keys, other hooks and groups kept; stale
  handlers replaced by one; bad JSON writes nothing; atomic write, mode kept,
  backup 0600; no false OK found.
- `git diff 9d8db2e..9b2c4f0 -- .claude/hooks` empty; the base guard equals
  the branch copy.
- Installed `~/.claude/settings.json` = the backup's four keys unchanged plus
  exactly the approved `hooks` object (parsed-JSON equality); its PreToolUse
  equals the branch project handler.
- Scope proportionate.

Missing proof (reason for INCOMPLETE): the NEW-session proof rooted at
`/home/claude` (deny probe blocked, allow probe passes, `--check` OK after the
merge). Hot reload in existing sessions is not that proof.

Remarks (non-blocking) and what was done:

| Remark | Action |
|---|---|
| `*` / `.*` matchers not seen as matching Bash | fixed: `matches_bash()` (empty, `*`, regex fullmatch); test `test_check_detects_catch_all_hook` |
| `"hooks": []` gives a traceback | fixed: clean "nothing written", rc 1; test `test_apply_refuses_hooks_not_an_object` |
| a second `--apply` overwrites the backup | fixed: the first (pre-guard) backup is kept; test `test_backup_keeps_the_first_state` |
| `--apply` replaces a symlink with a file | fixed: refuses a symlink; test `test_apply_refuses_symlink` |
| `--check` ignores `settings.local.json`, managed settings, project `disableAllHooks` | not changed; recorded as a known limit |
| guard changes on a task branch act only after merge | one line added to `docs/TWO-AGENTS.md` |

After the fixes: `test_install_command_guard.py` 29/29, full suite 134/134
(`logs/02-tests-after.txt`, `logs/03-full-suite.txt`). The installed handler
string is unchanged by these fixes.

## Round 2 (2026-09-29, same ephemeral Verifier, branch tip 0ac5199)

Verdict: **PASS** (PATCH_CORRECT), `REVIEWED` (not independently
reproduced: the Verifier read the new session's transcript, it did not start
a session itself).

- Tests 29/29 and the full suite 134/134, run by the Verifier. Round 2 does
  not touch `.claude/`.
- The Verifier tried to break the 8be3f62 fixes in a mktemp tree:
  - `matches_bash`: True for `*`, `.*`, `""`, None, `Ba.*`, `Bash|Edit` and
    the invalid regex `(`; False for `mcp__.*`, `Edit|Write`, `Monitor` and
    `bash`.
  - `{"hooks": []}` is refused cleanly.
  - A symlinked settings file is refused; the link and its target are
    unchanged.
  - The first backup is kept.
- The new-session proof was checked against the raw transcript
  `~/.claude/projects/-home-claude/ddfd321b-....jsonl`: cwd `/home/claude` on
  all 63 records; 19 hook errors carry the guard's own reasons, and the
  fallback "did not decide (rc=N)" never occurs. A subagent transcript is
  present (S8). The session root's project settings path is the user file
  itself, and there is no `settings.local.json`, so the user-level handler is
  what loaded.
- The installed `~/.claude/settings.json` is unchanged since round 1 (same
  sha256 8fdf9752..., same mtime).

Missing before DONE (the owner's post-merge checks, agreed with C; if either
fails, this PASS no longer holds):
- step 1: `--check` prints OK on base main;
- step 6: one guard run per call in a session rooted in `~/unity-distro`.

Marker-allow and the log line: May's open decision, outside this verdict.

Remarks (non-blocking):
- `matches_bash` uses `re.fullmatch`. If Claude Code matches unanchored, a
  matcher like `sh` would go unflagged. Impact is small: a deny still wins
  over another hook's allow.
- Hooks that match only `Monitor` are not checked.
