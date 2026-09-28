# UNITY-20260927-057: a narrow command-guard allowance for the aptly rehearsal

Owner: agent B. On 2026-09-28 May confirmed the task directly in B's session
(evidence JSON, `reason`): "UNITY-…-057 — yes, start by the normal process.
Use a narrow allowance in the hook; do not bypass the existing restriction.
After the implementation run the full set of tests and an independent
verification. On any new bypass or ambiguity stop and report, without
weakening the protection. After PASS the task goes through the normal merge
into main." The ID in May's message, 20260928-057, does not exist on the
board; this is 20260927-057.

The purpose is UNITY-20260927-047 phase R: rehearse the switch from a
repo-based to a snapshot-based publication on a scratch aptly (`aptly
publish repo/snapshot/switch/drop/show/list`). The command guard from 058
denies every `aptly publish`. 057 adds one allowance on top of it
(`_aptly_denial()`, the point 058 left for it), for a scratch aptly that
cannot reach the live repository in /srv/aptly.

```yaml
task_id: UNITY-20260927-057
package: unity-distro .claude/hooks/command_guard.py
issue: local - the guard denies the rehearsal the process needs (047 phase R)
status: REPRODUCED  # the rehearsal command is denied today (logs/01)
existing_fix_result: NOT_FIXED
invariant: >
  No Bash/Monitor command allowed by the guard can make aptly publish, drop or
  switch anything in, or read or write the database of, the live repository
  (/srv/aptly, ~/.aptly.conf); the allowance admits exactly one literal
  aptly publish command whose configuration confines every place aptly
  writes to the rehearsal root.
chosen_approach: see Design
design_challenger_required: true
design_review_result: APPROVE  # rounds 1-3 REVISE, round 4 APPROVE
architectural_task: false
package_change: false
```

## What aptly 1.6.2 reads (source, `utils/config.go`, `context/context.go`)

- **Config file.** `-config` names the file. Without it aptly reads
  `$HOME/.aptly.conf`, `/usr/local/etc` or `/etc` (058).
- **Parsing** (`LoadConfig`). JSON first, through `JsonConfigReader`, which
  strips `//` and `/* */` comments; if that fails, YAML. The file is decoded
  **into the defaults**, so a missing `rootDir` stays `$HOME/.aptly`. Go's
  `encoding/json` matches keys **case-insensitively**.
- **Where aptly writes or reads the repository:**
  - `rootDir`: db, pool and public by default;
  - `FileSystemPublishEndpoints.<name>.rootDir`;
  - `S3PublishEndpoints`, `SwiftPublishEndpoints` and `AzurePublishEndpoints`
    (remote);
  - `packagePoolStorage`: local `path`, or Azure;
  - `databaseBackend`: `type` leveldb or etcd, `dbPath`, `url`. Without
    these the database is `rootDir/db`.

Every one of these could point the rehearsal at the live repository. A
`databaseBackend.dbPath` of `/srv/aptly/db` with a scratch `rootDir` would
publish into the live database, for example.

## Design review round 1: REVISE

The challenger worked by reading the code; it ran nothing. Its findings:

1. `-distribution` and `-component` are joined into paths unchecked
   (deb/publish.go; files/public.go does not confine paths to its root).
   drop, switch and update act on the stored record.
2. On any JSON decode error aptly re-reads the file as YAML over what JSON
   has already set. Python and Go also disagree on NaN and Infinity, on
   UTF-16, on wrong value types, on null (Go keeps the default) and on the
   case of `type`. A strict schema is needed, not "strict JSON".
3. Every path field must be absolute, normalised and non-empty. Only
   `rootDir` gets `~` expanded; the other paths are relative to the Bash
   tool's working directory.
4. aptly derives db, pool, public, upload and skel from rootDir, so the
   whole root tree must be checked:
   - a symlink or a hard link planted by an earlier command could point
     into the live repository (PutFile truncates in place);
   - so could a bind mount, since sudo is available.
5. Aliases, functions and PATH from the user's profile apply to the Bash
   tool, so the command word must be an absolute path to the verified
   binary.
6. `-config` is the only flag that moves the roots. Count it across all
   arguments.
7. Environment: HOME, GNUPGHOME, LISTEN_*, OS_*/ST_* move no root once
   rootDir is required and `~` is denied.
8. databaseBackend: type absent or exactly "leveldb", `url` absent.
9. The config path itself (not only its realpath) must be a regular file
   inside the root.
10. The freeze conflict is a stop: the allowance must not be merged or
    enabled before the rule's wording follows May's decision.
11. Add a denial test for each item. The legacy floor only denies
    `args[0] == "publish"`, so it does not block `aptly -config=P publish`.
    That is intended and gets a test.

## Design (revised after round 1)

The allowance is checked in `_aptly_rules()` before rule E. It applies only
to the word `publish`; `task` and `api` stay denied. **All** of the
following must hold, otherwise the existing denial stands.

1. **Command shape.** The whole command is one group at one level:
   - `expansion` is false, and there is no heredoc, substitution,
     redirection, assignment or prefix;
   - token 0 is exactly `/usr/bin/aptly`. That file is root-owned, not
     writable by group or others, and is the same inode as aptly on PATH;
   - exactly one config flag in the form `-config=P` or `--config=P` (the
     `=` form only, so the value is not a separate token), placed before
     the word `publish`;
   - the first bare token is `publish`, and no other argument is `publish`,
     `task` or `api`;
   - no argument contains `..`.
2. **Root** `/var/tmp/aptly-rehearsal`:
   - lstat shows a directory, not a symlink, owned by the hook's uid, with
     mode not writable by group or others;
   - its realpath is not /srv/aptly, not inside it and does not contain it;
   - no mount point is at or under it (`/proc/self/mountinfo`).
3. **Tree walk** of the root (os.walk, links not followed):
   - every symlink resolves (realpath) inside the root;
   - every regular file's st_nlink equals the number of its links found
     inside the root;
   - no device, FIFO or socket files.
4. **Config file P.** Absolute, normalised, inside the root. lstat shows a
   regular file (not a symlink), owned by the hook's uid, not writable by
   group or others, at most 64 KiB.
5. **Config schema** (exact key spelling, exact types, no null):
   - the file is UTF-8 without a BOM, all bytes ASCII, and contains
     neither `//` nor `/*`;
   - `json.loads` with a duplicate-key hook (denied) and parse_constant
     (NaN and Infinity denied) yields exactly one object;
   - allowed top-level keys and their types:
     - `rootDir`: string, required;
     - `architectures`: list of strings;
     - `gpgDisableSign`, `gpgDisableVerify`, `dependencyFollowSuggests`,
       `dependencyFollowRecommends`, `dependencyFollowAllVariants`,
       `dependencyFollowSource`, `skipContentsPublishing`,
       `skipBz2Publishing`: bool;
     - `gpgProvider`, `logLevel`, `logFormat`, `downloader`: string;
     - `downloadConcurrency`, `databaseOpenAttempts`: int, 0..1000;
     - `FileSystemPublishEndpoints`: object of objects with `rootDir`
       (string, required) and `linkMethod` (one of hardlink, symlink,
       copy);
     - `databaseBackend`: object with `type` absent or exactly `leveldb`,
       and `dbPath` (string);
     - `packagePoolStorage`: object with `type` absent or exactly `local`,
       and `path` (string).

     Any other key at any level is denied.
   - Every path (`rootDir`, endpoint roots, `dbPath`, pool `path`) is
     non-empty, absolute and normalised, contains no `~`, and its realpath
     lies inside the root. For a path that does not exist yet, the nearest
     existing ancestor is resolved and the rest appended.
6. If every condition holds, the command is allowed. Rules A, E, R, C and
   the legacy floor are unchanged; the legacy floor does not match the
   rehearsal form (args[0] is `-config=`), and a test pins that.

7. **Authorization marker** (added after May's freeze decision,
   2026-09-28). The allowance applies only while C has recorded an active
   rehearsal authorization in `/home/claude/coordinator/rehearsal-authorization.json`,
   so that 057 is not a general whitelist and the permission ends by
   itself. The marker is a single strict-JSON object:
   `{"schema": 1, "task_id": "UNITY-...", "root": "/var/tmp/aptly-rehearsal",
   "authorized_by": "May", "recorded_by": "C", "not_before": "<UTC ISO>",
   "not_after": "<UTC ISO>"}`. The hook requires:
   - lstat shows a regular file, owned by the hook's uid, not writable by
     group or others;
   - the same strict parsing as the config (exact keys and types,
     duplicates denied);
   - `root` equal to the fixed root;
   - `authorized_by` exactly "May";
   - `not_before <= now < not_after`, and the window at most 24 hours.

   C removes the marker when the rehearsal ends; otherwise it expires.
   Limit: every agent runs as the same uid, so the file cannot be protected
   from an agent by permissions. Only the process rule stops an agent from
   writing it (section 6: agents never widen exceptions; the coordinator
   directory is C's). The marker binds the allowance to a recorded, dated
   authorization and limits it in time; it is not an authentication.

**Signing.** The rehearsal may sign with the real key through gpg. It only
signs files in the scratch root, and 047 phase R needs signed Release files
to compare. This is recorded, not restricted.

**Round 2 (REVISE) additions, adopted:**
- **Exact types.** `type(v) is int` for integers (no bool, no float),
  `type(v) is bool` for flags and `type(v) is str` for strings. A value that
  Go rejects would send aptly to its YAML fallback.
- **The walk fails closed.** `os.walk(onerror=raise)`: an unlistable
  directory denies. Directory symlinks (listed among dirnames) get the same
  symlink check as file symlinks.
- **Every directory** in the tree is owned by the hook's uid and not
  writable by group or others.
- **Decoded strings** (after `\u` escapes) are ASCII; a lone surrogate is
  denied.
- **The walk is bounded** to 200,000 entries; more denies. Mount points
  from `/proc/self/mountinfo` are compared after decoding its octal escapes
  (`\040` and the like).

**Round 3 (REVISE, minor) additions to the marker, adopted:**
- **Location pinned.** Exactly `/home/claude/coordinator/rehearsal-authorization.json`,
  and its realpath equals that path. `/home/claude/coordinator` is a real
  directory, owned by the uid and not writable by group or others.
- **Timestamps** only as `YYYY-MM-DDTHH:MM:SSZ` (UTC), with
  `not_before < not_after` and a window of at most 24 hours.
- **`reference`** (required, non-empty string): where May's approval is
  recorded, for example a PENDING-MAY entry or a coordinator log line.
- **`session_id`** (required) is compared with the `session_id` in the
  hook's input: the session of the task's owner. It is forgeable, but it
  stops another agent from using the allowance by accident.
- **Audit log.** Each allowed rehearsal command is appended as one JSON
  line to `/home/claude/coordinator/rehearsal-log.jsonl` (UTC time, session,
  command, sha256 of the marker). If the append fails, the command is denied.
- **Rejected by the challenger:** a one-shot marker (the rehearsal needs
  several commands), a command counter (as forgeable as the marker), and
  reading the task board from the hook (fragile).
- **Section 6** now says the authorization takes effect only through C's
  dated marker, and that "ends automatically" means C removes the marker
  or it expires.

**Round 4: APPROVE.** Notes taken into the implementation:
- The audit log is opened with O_NOFOLLOW and O_APPEND, with the marker's
  owner and mode checks.
- A log line records that the hook allowed a command, written before the
  command runs. It is not a record of what the command did.
- Subagents of the owner's session send the same session_id, so the
  allowance covers them. This is accepted and recorded.

**Merge and use.** The freeze decision comes first (see unknowns).

## Not covered (unknowns)

- **Environment aptly reads** (round 1): HOME (default config, default
  rootDir, `~` in rootDir), GNUPGHOME, LISTEN_PID/LISTEN_FDS, and OS_*/ST_*
  (Swift). None moves a root once rootDir is explicit and `~` is denied.
  LD_PRELOAD and the like are same-user limits of any hook.
- **The rehearsal database** must be created fresh for the rehearsal. A
  copy of the live database would carry published records, and drop,
  switch and update act on the stored records. The hook cannot inspect a
  leveldb; this belongs to the 047 procedure.
- **Time of check against time of use.** The config file or the root
  could be changed between the hook's check and aptly's run by another
  process of the same user. Only the owner can write to the root and the
  file, and it is the owner's own session. This is recorded, not solved.
- **Freeze policy, decided.** May's decision (2026-09-28, via C) is
  option 1: a rehearsal exception, as now written in ENGINEERING-PROCESS
  section 6. The freeze protects the live state. Only May declares and lifts
  a freeze, and C records it. Direct publish is denied by default. The
  rehearsal exception covers only the rehearsal phase of a task May
  authorized, on an isolated state, checked by the guard. It gives no right
  to /srv/aptly and ends with the rehearsal. The authorization marker
  (design item 7) is the hook-side binding. Freeze no. 1 is in force (May,
  2026-09-27, until 057 is complete), and 047 R does not run before 057 is
  merged.
- 047's blocked-commands.md uses a scratchpad path. It will have to use
  /var/tmp/aptly-rehearsal/aptly.conf.

## Implementation

The code is `.claude/hooks/command_guard.py` (the "aptly rehearsal
allowance" block): `_check_rehearsal`, `_check_root`, `_strict_json`,
`_check_config`, `_check_marker` and `_log_rehearsal`.

- `inspect(command, session_id)` receives the session from the hook input
  (`main()`). The legacy floor comes first, as before.
- A command meant as a rehearsal (aptly as its first word, a config flag
  and the word publish) goes through `_check_rehearsal`. Any failure
  denies with the reason, and on success only the non-aptly rules remain.
- Every other command goes through 058's `_aptly_rules`, unchanged.
- The command shape is enforced by one character-set regex: single spaces,
  `[A-Za-z0-9_./=:,+@-]` only. That rules out quoting, expansion,
  redirection, separators, newlines and comments in one check.

`docs/ENGINEERING-PROCESS.md`: section 6 now has the freeze rule as May
decided it, with the marker sentence; section 9 has one paragraph on the
allowance.

## Result

- `scripts/tests/test_command_guard_rehearsal.py`: 20 tests. They load the
  hook module with its root, coordinator directory, marker and log in a
  temporary directory, so every check runs against real files. Nothing is
  executed.
  - Allowed: `publish list` and `publish repo ...` with a complete marker,
    both logged as JSONL; a config with every path field inside the root;
    links and hard links that stay inside the root.
  - Denied: the marker missing, expired, future, over 24 hours, reversed,
    with an offset, not May's, not recorded by C, for another root, for
    another session, or without a session; a wrong schema (also as a
    bool); extra or missing keys; an empty reference; a group-writable or
    symlinked marker; a group-writable coordinator directory.
  - Denied, command shape (23 cases): no absolute binary; the space form
    of -config; two configs; the config after publish; `..`; separators;
    redirection; a pipe; extra spaces; quoting; expansion; task; api;
    publish twice; an assignment; env; sudo; a relative config, one
    outside the root or not normalised; a second line.
  - Denied, config content (25 cases): rootDir missing, live, outside,
    with `~`, relative, with `..`, a number or empty; dbPath live; the db
    type etcd or LevelDB, or a url; the pool outside or azure; an endpoint
    live or with a bad linkMethod; S3, Swift or Azure endpoints; a key in
    another case; an unknown key; a bool as int; an int out of range; not
    an object.
  - Denied, encoding (12 cases): duplicate keys, null, NaN, float, a block
    or line comment, non-ASCII raw, escaped or as a lone surrogate, two
    values, YAML, a BOM. Also a symlinked or group-writable config.
  - Denied, root and tree: the root group-writable or a symlink; a
    directory, file or hard link leading outside; a FIFO; a group-writable
    or unlistable subdirectory; too many entries. A symlinked or
    world-writable audit log is denied too.
  - The legacy floor does not match the rehearsal form, and a test pins
    that. Through the real hook process, without C's marker, the rehearsal
    command stays denied.
- `logs/02-denial-reasons.txt` lists the denial reason of each negative
  case, so each is denied by its own check and not by a failure elsewhere.
- The full suite passes: 90 tests (`python3 -m unittest discover -s
  scripts/tests`).

## Status

IMPLEMENTING -> VERIFYING (independent Verifier).
