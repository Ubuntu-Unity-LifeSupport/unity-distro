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
design_review_result: PENDING
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
