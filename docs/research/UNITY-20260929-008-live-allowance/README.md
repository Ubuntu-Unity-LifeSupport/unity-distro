# UNITY-20260929-008 - command_guard allowance for the live phase L commands of UNITY-20260927-047

```yaml
task_id: UNITY-20260929-008
task_kind: tool
package: unity-distro .claude/hooks/command_guard.py
target_series: resolute
issue: phase L of UNITY-20260927-047 (move live aptly ./resolute to snapshot publication) needs live `aptly publish` commands; the guard denies every live publish in an agent session, and May chose to extend the guard rather than run them himself (C, 2026-09-29; May confirmed to B in session b7902aab)
status: REPRODUCED (the need: every L publish command is denied today)
existing_fix_result: NOT_FIXED (the 057 allowance covers only /var/tmp/aptly-rehearsal)
architectural_task: false
design_challenger_required: true
design_review_result: APPROVE  # round 1 REVISE, round 2 APPROVE (design v2)
```

## Requirements (C, 2026-09-29)

- Admit ONLY the exact L commands from a reviewed list: no grammar, no
  "similar" command. The list lives in the repository; C's marker carries its
  sha256.
- A marker as in 057: written only by C after May's GO; one session; a time
  window; task_id UNITY-20260927-047; root /srv/aptly. A separate file or kind,
  so that the rehearsal marker and the L marker cannot stand in for each other.
- Every allowed command is logged.
- Everything else stays denied: the rehearsal, another session, an expired
  marker, an extra flag, another path.
- Fail closed if the guard fails (the UNITY-20260928-012 handler already does).
- Regression tests: allowed by the list; denied for every deviation. An
  independent Verifier. It takes effect only after C merges to main; proof
  in a new session.

## Current behaviour (FACT, main 99629d9)

`inspect()` first applies the legacy floor, `_group_rules(_legacy_groups())`,
which denies `aptly publish ...` whenever `publish` is aptly's first argument
("Publish through scripts/publish_aptly.py"). Only after that does it
recognise a rehearsal candidate (a `-config` token plus `publish`). The L
commands use the live default config (`~/.aptly.conf`, `rootDir`
/srv/aptly), have no `-config`, and so are denied by the floor.

## Design (proposed)

1. **List file** `.claude/hooks/live-commands.json`, next to the guard in main:
   `{"schema": 1, "task_id": "UNITY-20260927-047", "root": "/srv/aptly",
   "aptly_conf_sha256": "<sha256 of ~/.aptly.conf>", "commands": [...]}`.
   The commands are the eight publish commands of phase L, byte-for-byte:

   ```
   /usr/bin/aptly publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047 candidate
   /usr/bin/aptly publish show resolute candidate
   /usr/bin/aptly publish drop resolute
   /usr/bin/aptly publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047
   /usr/bin/aptly publish show resolute
   /usr/bin/aptly publish repo -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute
   /usr/bin/aptly publish list
   /usr/bin/aptly publish drop resolute candidate
   ```

   The non-publish L commands (`snapshot create`, `repo show`, `snapshot
   show/list`) are already allowed by the 058 rules and are not listed.
2. **Match.** The command string must be exactly equal to one entry: no
   normalisation, no whitespace tolerance. Only then is it a live candidate.
   Anything else takes today's path unchanged.
3. **For a live candidate, before the legacy floor:**
   - the list file is a strict JSON file (057's `_strict_json`: regular, not
     a link, owned by the user, not group/other-writable, ASCII, no duplicate
     keys) with exactly the schema keys; every entry matches the 057 plain
     shape, starts `/usr/bin/aptly publish `, and entries are unique;
   - the marker `~/coordinator/live-authorization.json`, a separate file from
     `rehearsal-authorization.json`, with exactly the keys schema,
     kind (`"live-publish"`), task_id, root (/srv/aptly), authorized_by (May),
     recorded_by (C), not_before, not_after, reference, session_id,
     commands_sha256;
     - its `commands_sha256` must equal the sha256 of the list file's bytes;
     - session_id must equal the hook payload's;
     - the window must be valid now and at most 6 hours (057: 24 h);
     - `~/coordinator` must be owned and not group-writable;
   - `/usr/bin/aptly` is root-owned, not writable, and the `aptly` on PATH
     (057's check);
   - `~/.aptly.conf` (from `pwd`, and `$HOME` must equal it) is a strict
     file whose sha256 equals the list's `aptly_conf_sha256`, so the config
     aptly will read is the reviewed one (`rootDir` /srv/aptly, no
     endpoints);
   - every check passes, then one line goes to
     `~/coordinator/live-log.jsonl` (time, session, task, command, marker
     sha256, list sha256), then allow. Otherwise deny with the reason.
4. The rehearsal path is unchanged, and it cannot accept the live marker (a
   different file, a different key set). The live path cannot accept the
   rehearsal marker. A rehearsal-shaped command is never a live candidate,
   because it is not in the list.

## Alternatives

- May runs the live commands in his own terminal (plan a260d8d). Rejected
  by May's choice.
- A grammar ("publish snapshot|drop|show with these flags"). Rejected by the
  requirement: exact list only.
- Relaxing the legacy floor generally. Rejected: the bypass is only for an
  exact listed string with a valid marker.

## Validation plan

`scripts/tests/test_command_guard_live.py` (057-style: module constants
pointed at a temporary coordinator directory, home and list; commands passed
to `inspect()`, nothing executed):

- allowed: each listed command with a valid marker, logged once;
- denied:
  - no marker; the rehearsal marker only; a marker of another kind, session,
    task or root; expired or future; window > 6 h; a wrong or missing
    commands_sha256; an extra key;
  - a list edited after the marker; the list a symlink or group-writable;
  - `~/.aptly.conf` changed, a symlink, or `$HOME` different;
  - one extra space, an extra or missing flag, another snapshot name, `aptly`
    without the path, a `-config=` form, a separator or redirection appended,
    a prefix like `env`/`sudo`;
  - `~/coordinator` group-writable; the log a symlink.
- The existing suites are unchanged (the 058 and 057 tests pass).
- The 012 handler test stays green.

Live proof in a new session after the merge (C merges): with a marker,
harmless only, **no live L command before May's GO for the run itself**. The
proof is inspect() via the hook payload (JSON fed to the guard, not
executed) with the marker present, plus the probe that a non-listed live form
is denied by the running hook.

## Design Challenger round 1: REVISE (2026-09-29) - design v2

Changes, by DC point:

1. **Shell function shadowing (accepted limit, best-effort deny).** The Bash
   tool sources a profile snapshot (`~/.claude/shell-snapshots/*`), and a
   function named `/usr/bin/aptly` runs instead of the binary (DC checked
   this in bash). A command string cannot defend against that; 057 recorded
   it as the same-uid limit F4. For the live path, deny when any file in
   `~/.claude/shell-snapshots/`, `~/.bashrc`, `~/.profile`,
   `~/.bash_profile` or `~/.bash_aliases`:
   - defines a function or alias whose name contains `aptly`;
   - sets `BASH_ENV`;
   - installs a `DEBUG` or `RETURN` trap.

   The guard's own `BASH_ENV` is checked too. Recorded as best effort.
2. **No `$HOME` dependency.** Every entry passes an explicit
   `-config=/home/claude/.aptly.conf` right after `/usr/bin/aptly`, and the
   guard checks that file's sha256 against the list's `aptly_conf_sha256`.
   The live exact match runs before `_rehearsal_candidate`. The rehearsal
   path still rejects any config outside /var/tmp/aptly-rehearsal. The entries:

   ```
   /usr/bin/aptly -config=/home/claude/.aptly.conf publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047 candidate
   /usr/bin/aptly -config=/home/claude/.aptly.conf publish show resolute candidate
   /usr/bin/aptly -config=/home/claude/.aptly.conf publish drop resolute
   /usr/bin/aptly -config=/home/claude/.aptly.conf publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047
   /usr/bin/aptly -config=/home/claude/.aptly.conf publish show resolute
   /usr/bin/aptly -config=/home/claude/.aptly.conf publish repo -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute
   /usr/bin/aptly -config=/home/claude/.aptly.conf publish list
   /usr/bin/aptly -config=/home/claude/.aptly.conf publish drop resolute candidate
   ```

   The -047 blocked-commands.md phase L section is updated to these exact
   strings, with B running all of them.
3. **GNUPGHOME / gpg config: accepted.** They change the signer, not where
   aptly writes: rootDir comes from the pinned config, which has no
   endpoints and no `~`. A different keyring means a wrong signature, which
   L4 catches (signer fingerprint 29A893E0...C27B152C).
4. **Tool restriction.** A live entry is admitted only when `tool_name ==
   "Bash"` and `run_in_background` is not true. `main()` passes both to the
   live check. Monitor and background calls are denied, so no drop can
   overlap a republish.
5. **Marker.** The rehearsal check rejects a marker whose key set is the
   live one, and the live check rejects the rehearsal key set; tests cover
   both directions, including across files. `reference` names May's GO and
   B's L0 backup and preflight record, so C writes the marker only after
   L0. The window stays at 6 hours at most.
6. **List file.** It lives at a fixed absolute path,
   `/home/claude/unity-distro/.claude/hooks/live-commands.json` (the guard's
   base checkout), never relative to cwd. A same-uid edit breaks the
   `commands_sha256` binding. The list itself is validated: schema, task_id,
   root, unique plain-shape entries, each starting
   `/usr/bin/aptly -config=/home/claude/.aptly.conf publish `. Changes follow
   C's merge rule. -047's DONE step removes the list from main together
   with the marker.
7. **Log.** `~/coordinator/live-log.jsonl` records "admitted", not
   "executed": time, session, task, tool_name, cwd, command, marker sha256
   and list sha256. It is opened `O_APPEND|O_NOFOLLOW` and must be owned
   and private. A failed write means deny.
8. **A lone `publish drop resolute` is accepted.** An outage without the
   republish is covered by the restore procedure: the L5b file restore, or
   the listed L5a `publish repo`. A stateful guard would become a grammar.
9. **Tests added to the plan:**
   - tab, trailing newline, CRLF and Unicode look-alikes;
   - malformed lists: a non-plain entry, a duplicate, a wrong prefix, a
     rehearsal-form entry;
   - a config sha mismatch;
   - Monitor or background calls, which must be denied;
   - a failed log write, which must deny;
   - markers swapped in both directions;
   - the 057 rehearsal still allowed while a live marker exists;
   - an end-to-end `main()` payload;
   - snapshot and rc functions, which must deny;
   - a corpus diff: only the eight listed strings newly allowed.

   Function shadowing itself stays documented, not tested.
10. **Docs are a stop condition.** A "live-phase exception" paragraph in
    ENGINEERING-PROCESS section 6 and a live-path item in section 9 merge
    with the code. The draft below states what May decided, and C and May
    confirm the wording at merge.

Draft for section 6, after the rehearsal exception:

> - **Live-phase exception.** For the live phase of a task that May has
>   explicitly authorized (first: UNITY-20260927-047 phase L), the command
>   guard admits only the exact command strings of the reviewed list
>   `.claude/hooks/live-commands.json`, byte for byte, as one foreground
>   Bash call. It checks that the pinned aptly config is unchanged. It takes
>   effect only through C's dated marker
>   `~/coordinator/live-authorization.json` (May's GO; one session; at most
>   6 hours; the list's sha256; a reference to the task's backup and
>   preflight record) and logs every admitted command to
>   `~/coordinator/live-log.jsonl`. It covers nothing else. Known limit: a
>   shell function defined in the agent's own profile could stand in for the
>   binary; the guard only refuses when it finds one. It ends when the live
>   phase ends: C removes the marker and, at the task's DONE, the list.

Draft for section 9:

> - The live-phase exception of section 6 (UNITY-20260929-008) admits only
>   the strings of `.claude/hooks/live-commands.json`, each starting
>   `/usr/bin/aptly -config=/home/claude/.aptly.conf publish`, as a
>   foreground Bash call, with C's live marker naming the session and the
>   list's sha256. Each admitted command is logged to
>   `~/coordinator/live-log.jsonl`.

DC round 2: **APPROVE** (design v2), with four implementation notes:

1. test the denial reason for near-misses;
2. check the pinned config's content, not only its sha;
3. keep the best-effort wording;
4. change the section 6 Default bullet to "except as allowed by the
   exceptions below".

All four are done.

## Implementation and validation record

Branch `b/UNITY-20260929-008`.

- `.claude/hooks/command_guard.py`:
  - live-phase block before `inspect()`: `_check_live`, `_live_list`,
    `_check_live_config`, `_check_live_shell`, `_check_live_marker`,
    `_log_live`, `_check_aptly_binary`;
  - `inspect()` takes `tool_name` and `background`, and checks a string that
    starts with the live prefix first;
  - `main()` passes the payload's `tool_name` and `run_in_background`.
- `_strict_json(..., private=False)` for the list only. In the git checkout
  the list is 0664 (umask 0002), and its integrity comes from the marker's
  `commands_sha256`. Owner and file type are still checked. The pinned
  config keeps the strict owner-private check.
- `.claude/hooks/live-commands.json`: the eight strings of design v2.
  `aptly_conf_sha256` is
  `ece05ab8ad8469cdeaa39487013830d7a9304cc09cf9989a18543193d8831b25` (the
  current `~/.aptly.conf`).
- FACT: `~/.aptly.conf` is 0664 today, so the guard denies it (group
  writable). -047's L0 must run `chmod g-w ~/.aptly.conf` before the marker;
  this does not change the content or the sha.
- `docs/ENGINEERING-PROCESS.md` section 6 (Default wording; live-phase
  exception) and section 9 (live path), as drafted. C and May confirm the
  wording at merge.
- Tests (`scripts/tests/test_command_guard_live.py`, 22 tests, all the cases
  of the plan):
  - against the unmodified guard (origin/main 99629d9): 1 FAIL and 47
    ERROR (logs/01);
  - after the change: 22/22 OK (logs/03);
  - full suite: 156/156 OK (logs/04).
- Corpus (058 `corpus.py`, 14 transcripts, 6850 unique real commands, guard
  on main vs new): 0 newly denied and 0 newly allowed (logs/02). Without a
  marker, the listed strings stay denied.

Next: the independent Verifier; C merges; proof in a new session (feeding
hook payloads, nothing executed). -047's blocked-commands.md phase L is
rewritten to these strings with B running them when -047 resumes.
