# Phase 5: signer routine policy and publisher integration (UNITY-20260929-024)

Permission model phase 5. Kind: `tool`, SECURITY. Owner: the architecture
session, by May's GO of 2026-10-09 ("Начинай P5"). Builds on the merged
UNITY-20260929-021 code (`signer/signer_core.py`, `signer/aptly_signer.py`,
`scripts/signer_client.py`, `scripts/gpg_standin.py`), the UNITY-20260929-019
design with the -021 amendments (a), (b), (c), and the architecture review
section 4.4 with May's decision 4 (`README.md`).

Not in this phase, by May's GO item 5: real publications, moving or rotating
keys, trust-policy changes, the first live publication, the service
installation. Those are May's steps 3-5 of -019; this phase gives them the
code, the tests, the files and the runbook.

## 1. Invariant (May, decision 4)

The signer signs a proposal without May only when a deterministic policy
classifies it as routine: one already-known source package; at most 40
binary records; no new or changed maintainer scripts relative to the
version it replaces; at least 10 minutes since the last automatic signature;
at most six automatic signatures per UTC day. It verifies the exact
composition, versions, architectures, checksums and provenance of the
artifacts itself. Any mismatch, anything it cannot verify, anything outside
the limits: no automatic signature, the proposal waits on the console. A
new package is never routine. Everything `propose` refuses today stays
refused.

The -021 invariant is unchanged: the signer signs only its own Release,
built from its template over content it checked, for an approval bound to
the current last-live and used once; scheduled re-signing covers last-live
only.

## 2. Policy file

`policy.json` on the signer, next to the template, named in the service
configuration (`policy`), read at every proposal so May's edits apply
without a restart. A change to it is a trust-policy change: May only
(decision 7). Missing file, unreadable, wrong schema, or any field of the
wrong type or range: **no automatic approval**, the proposal goes to the
console, and the console `list` says why (fail closed). The committed
reference copy is `signer/policy.json`:

```json
{"schema": 1, "auto_approve": true,
 "max_sources": 1, "max_binary_records": 40,
 "min_interval_seconds": 600, "max_per_utc_day": 6}
```

`auto_approve: false` is the kill switch; the service then behaves exactly
as merged today (every proposal to the console). The numbers are May's
(decision 4); the code enforces them as written, and refuses a policy
whose numbers are below 1 or whose `max_sources` is above 1 (the
architecture allows one source per routine set; a larger number is a
policy change the code does not accept without a schema change).

## 3. Routine classification

`signer_core.routine(state, pid, policy, now) -> (ok, reasons)`, pure,
over the stored proposal: its diff (computed by the signer from the index
set it checked), the entries it validated, the `.deb` facts it read itself
(amendment (b)), the task id builder claimed, and the signer's own
auto-approval history. Never from text builder sent. Every reason is a
printable string, logged and shown on the console.

Routine only if ALL hold:

1. **A base exists.** `last_live` is set; an empty repository is never
   routine (the first publication under the new key is May's, decision 8).
2. **Only additions.** Every diff row is `added`. A `removed` row, or a
   `changed` row (same name, version and arch with other bytes), is not
   routine.
3. **Exactly one known source.** The source name of every added row
   (Sources rows: `Package`; Packages rows: the first word of `Source`,
   else `Package`) is one and the same name, it is the source of at least
   one entry in `last_live` (by the same rule), and `max_sources` is 1.
4. **Upgrade only.** For every added row, `last_live` holds at least one
   entry with the same `(index, package, arch)`, and the new version is
   strictly greater than each of them in Debian ordering
   (`signer_core.version_compare`, a pure implementation of the dpkg
   algorithm, tested against the table `scripts/tests/data/dpkg_version_order.json`
   generated with `dpkg --compare-versions` on builder: 3136 pairs).
   A binary that `last_live` does not list under that name and arch is a
   new binary, hence not routine, even when its source is known. The
   highest previous version of each added `(index, package, arch)` must
   name the same source (rule 3's derivation): a binary name taken over by
   another source is a composition change for the console.
5. **Provenance.** Every added Packages row's source version (the version
   in `Source: name (version)`, else the binary's own) equals the version
   of the added Sources row of that source when one is in the proposal, and
   all added Packages rows name the same source version. When the
   proposal carries no Sources row (a binary-only index set), the source
   version is the binaries' own and must be the same for all of them.
6. **Record count.** Added Packages rows are at most `max_binary_records`.
7. **Maintainer scripts unchanged.** For every added Packages row, the
   signer's script map of the `.deb` (member names and sha256 of each of
   `preinst`, `postinst`, `prerm`, `postrm`, `config`, read from the control
   archive it validated) equals the stored script map of the highest
   previous version of the same `(index, package, arch)` in `last_live`.
   A previous version without a stored map (content that went live before
   this phase, or was adopted without its `.deb`s) is not routine; so is
   any difference in names or hashes, and so is an added row whose `.deb`
   was not read in this proposal (its SHA256 already in last-live under
   another name: no map, not routine). "No scripts" equals "no scripts".
8. **Rate.** The last automatic approval is at least `min_interval_seconds`
   ago, and fewer than `max_per_utc_day` automatic approvals fall in the
   current UTC day (`state["auto_signed"]`, kept for 2 days).
9. **Task id.** The proposal's task id matches `UNITY-YYYYMMDD-NNN` and
   differs from the task id of every automatic approval in
   `state["auto_signed"]` (two automatic signatures for one task need the
   console). The id is builder's claim and the history is pruned after
   2 days: this is a rate rule, not an identity check.
10. **Policy present and sane** (section 2) and `auto_approve` true.
11. **The signer has signed before.** `state["current"]` is set: content
    signed by this signer's key has gone live (a publication May approved
    on the console, or the re-sign of the content he adopted, section 5).
    Decision 8 is thereby in code, not only in the runbook: after
    `adopt-live` nothing is automatic until May's first signing.

Stated consequences, accepted under decision 4: a source that stops
shipping one of its binaries is routine (the old binary stays live at its
old version); an epoch introduction is an upgrade by dpkg ordering; "per
UTC day" allows the daily quota twice across midnight.

When routine, `propose` calls `approve` itself with `approved_by:
"policy"` and logs `auto-approved by policy: <pid> <task> <source>
<version> (<n> binaries)`; `state["auto_signed"]` gains `{at, task_id,
pid, set_id}`. The console `list` shows pending proposals as today and,
below them, the automatic approvals since the last console view with the
same diff lines May would have seen (`console_lines`), so he reviews after
the fact. When not routine, the proposal stays pending as today and the
console `show` prints the reasons under `policy:`.

`sign`, `live`, `resign` are unchanged: an automatic approval is an
approval like May's, bound to its base and used once.

**Idempotent proposals.** A second `/propose` of the same content
(`set_id`) on the same base returns the pending proposal of it, or its
approval when that approval is unused (`status: approved`) and bound to
the current last-live, instead of a new entry (the publisher rerun after
May approves on the console must not create a second pending copy). An
approval in any other status (signed but not live after a failed switch,
consumed) is not returned: the rerun creates a new proposal, which the
policy evaluates again, and rule 9 then sends it to the console, since the
task was already signed automatically once. `sign` prefers a usable
approval, so the new one works. The answer carries `status: approved |
pending`, `proposal`, `approved_by` and `reasons`.

## 4. Script maps through the state

- `aptly_signer.script_scanner` returns, besides the text flag the console
  shows, the map `{name: sha256}` of the script members; `control_members`
  returns names with the member bytes' sha256 (the raw ustar walk already
  has the sizes and offsets).
- `propose` stores per proposal `scripts: {entry key: map}` for every
  Packages entry whose `.deb` it checked (added, or changed under the same
  key), and copies the stored map of unchanged entries from `last_live`.
- `approve` carries `scripts` into the approval; `live` carries it into
  `last_live`. State schema stays 1: a state without `scripts` reads as
  "no map known" (not routine), which is the safe reading.

## 5. Adopting the live content (May's cut-over step 4, in code)

At cut-over the signer's state is empty while the repository holds ~280
`.deb`s, more than `/propose` can carry (72 MiB) and more than May should
read as a diff. New console command **`adopt-live`**: the signer fetches
`dists/<distribution>/` of the repository (`repo_base`, the hardened fetch
of -021: no redirects, size caps) - the index files the template allows and
`Release` - checks the index set exactly as a proposal, builds its own
Release and compares it with the served one (Date and Valid-Until apart;
the served `Contents-*` are not listed by the template, so the served
Release must already be a `-skip-contents` one: precondition below), fetches
every `.deb` the Packages lists (capped at its `Size`, sha256 checked) and
reads its script map, shows May the summary (entries, sources, how many
with scripts, `set_id`, the served Release's Date) and, after he types
`adopt`, sets `last_live` with entries and script maps. No approval, no
signature, nothing served changes; `current` stays unset until the first
signing. Everything after that is the ordinary flow: the first live
publication under the new key is May's by rule 11 (section 3): either the
re-sign of the adopted content or a console-approved proposal.

Fetch order: the served `Release` first, then exactly the files it lists
that the template allows (an allowed file the Release does not list is not
fetched; a listed file the template does not allow refuses). The adopted
set's index files are stored like a signed set's, so `resign` can re-sign
the adopted content under the new key and `refresh --current` installs it:
that is the cut-over under the new key without any package change, and it
is May's (he types `adopt`, runs `resign`, runs the refresh). Rule 11 keeps
everything manual until that signing.

`adopt-live` refuses: a non-empty `last_live` (adoption happens once), a
served Release that does not match the template, any `.deb` that fails the
-021 checks. The served content is the one input the signer takes from the
repository unverified; May checks the summary (entries, sources, content
id, the served Date) against the repository he knows before typing
`adopt`.

## 6. Publisher integration (UNITY-20260929-024)

`publish_aptly.py` is the only program that runs `aptly publish` for the
live repository. Its signer mode is enabled by the presence of the client
configuration `~/.config/aptly-signer/client.json` (a trusted directory:
Edit asks May, the shell may not write it, phase 3), which May creates at
cut-over; without it the publisher runs today's path unchanged (local gpg,
no proposal) and says so in its output. This keeps the rollback of the
architecture row 5 (the previous path works until the old key leaves
builder) without a code revert.

Legacy mode is recorded: the write-once record carries `signer: {"mode":
"legacy"}` so that a publication made under the local key during the
rotation window is visible after the fact; the window closes by itself
when the old key leaves builder (gpg fails, the publisher fails closed).

In signer mode, after the switch-time apt view (`compare_views`) and
before C's approval is consumed:

1. **Repository state.** The served `InRelease`'s `Valid-Until`, read from
   the file (absent, as in aptly's own Release before the first signer
   publication: pass): if it has passed, fail with "the repository has expired
   (Valid-Until passed): the cadence refresh did not run or was refused;
   see the refresh marker" (exit 2; -021 round 3). Leftover `*.tmp` under
   `dists/<distribution>/` are reported ("the last switch was refused;
   aptly leaves *.tmp files that the next switch overwrites") and not
   deleted (-021 (d)).
2. **Proposal publication.** The gated snapshot is published from the
   live aptly database into a separate tree, never into
   `/srv/aptly/public`: a configuration file written for this run under
   `/var/tmp/aptly-rehearsal/<task>/` equal to `~/.aptly.conf` plus one
   `FileSystemPublishEndpoints` entry `proposal-<task>` with `rootDir` =
   `/var/tmp/aptly-rehearsal/<task>/public` and `linkMethod: copy` (the
   whole snapshot pool is copied, 308 MB today; the same filesystem would
   allow hardlinks, copy is the safer choice); then `aptly -config=<that
   file> publish snapshot -skip-signing -skip-contents
   -architectures=<the Architectures line of the live Release>
   -distribution=<distribution> -component=main <snapshot>
   filesystem:proposal-<task>:<prefix>`. The endpoint is per task, so two
   tasks (one pending, one running) never drop each other's publication;
   a rerun of the same task drops and republishes its own. `chmod -R go-w`
   on the tree afterwards (deviation 3).
3. **Propose.** `signer_client.propose(<tree>/public, task)`: the index
   set the signer signs and every `.deb` whose SHA256 is not in the live
   Packages. The answer's `status`:
   - `approved` (by policy, or by May on the console for a rerun): go on;
   - `pending`: exit 3 with "waiting for May on the signer console
     (proposal <pid>); rerun after approval; the proposal and C's approval
     stay valid while the base is last-live and the window is open". No
     approval consumed, no record, no aptly switch. (aptly's own exit
     status is still returned verbatim by the switch step, as today; the
     message, not the number, is the signal.)
   - a refusal or an unreachable signer: exit 2 with the reason; nothing
     consumed.
4. **Switch.** C's approval is consumed and the switch runs as today
   (`-skip-contents` added, belt and braces: the live publication keeps
   its setting), with the publisher's own environment: `PATH` starts with
   a directory holding `gpg -> scripts/gpg_standin.py` of this checkout
   (-021 (c)); the stand-in reads `~/.config/aptly-signer/standin.json`
   (May's file). A refusal at the switch leaves the old trio live (proven
   in the rehearsal) and ends the run as today's aptly failure (approval
   marked failed, no record). A switch that signed but failed afterwards
   (aptly error after the stand-in answered) leaves a signed, unused
   approval: the rerun's proposal is new; when the first approval was
   automatic, rule 9 sends it to the console; after a console approval it
   is evaluated on its content like any proposal.
5. **Refresh and live.** `signer_client.refresh(task, switch=True)`, then
   `/live` **whether or not the refresh succeeded** (the served InRelease
   is the signer's either way, and `/live` moves last-live so the cadence
   can repair the trio). A failed refresh: the client leaves the marker and
   the `REFRESH-FAILED` line (-021 R4); the publisher writes the record
   with `signer.refresh: FAILED` and exits 2 after the record. A failed
   `/live`: `signer.live: FAILED`, exit 2 after the record; the recovery is
   `scripts/signer_client.py live` run by hand (safe: the signer accepts
   only its own signed, unconsumed InRelease on the current base); until
   then the cadence refresh is refused by R2 and the repository expires
   visibly (-021 R3). Both are reported with the reason.
6. **Record.** The write-once record gains `signer: {proposal,
   approved_by, set_id, inrelease_sha256, refresh, live}`; schema stays 1.
   `taskctl.py` `PUBLISHED` is unchanged.
7. **Cleanup.** The proposal publication is dropped and its tree removed
   at the end of a run that reached the switch; a `pending` exit keeps
   nothing either (the rerun republishes; the tree is a copy).

The publication tools list (`approval_record.PUBLICATION_TOOLS`) gains
`scripts/signer_client.py`, `scripts/gpg_standin.py` and
`signer/signer_core.py`: the task branch's copies must equal
`origin/main`'s (phase 4), since the publisher runs them.

**Cadence.** `signer/builder/aptly-signer-refresh.service` and `.timer`
(systemd user units, installed by May; `loginctl enable-linger claude` so
the timer runs without a login): every 12 h,
`scripts/signer_client.py refresh --task cadence --current`. `--task`
accepts the literal `cadence` besides a task id; the marker is
`cadence.refresh-failed`. The signer-side `resign` timer must run well
inside `valid_days` (3): every 12 h as well.

**Client configuration** (`~/.config/aptly-signer/client.json`, May's
file; the client validates the keys on load and refuses a missing one):
`url`, `public_root`, `keyring`, `store`, `marker_dir`, `log`;
optional `distribution` (default `resolute`) and `timeout` (120).

## 7. May's steps (unchanged in substance; the runbook is section 10)

`policy.json` content and `auto_approve`; the VM and the `never_allowed`
entry; the service, key and keyring; the cut-over precondition: republish
the live distribution once with `-skip-contents` under the current local
key so that aptly's Release lists no `Contents-*` (the template has none;
the signer would otherwise refuse every Release); `adopt-live`; the client
and stand-in configurations on builder; the first live publication (May
approves on the console); the cadence timer; the rotation. Rollback
(decision 5) is not automated: a switch to an earlier set is a proposal
with `removed` rows, which the policy sends to the console.

## 8. Tests

- `test_signer_core.py`: one positive routine case; one refusal per rule
  1-11, each changing exactly one thing; the kill switch; a missing,
  malformed and out-of-range policy; the day boundary and the interval;
  the task-id repeat; idempotent proposals; script maps carried through
  approve and live; a `last_live` without maps is not routine;
  `version_compare` against the dpkg table.
- `test_signer_end_to_end.py`: the real service with a policy file: a
  routine upgrade auto-approves and the console `list` shows it with its
  diff; a new source waits; a changed script waits; the kill switch and a
  missing policy file; `adopt-live` from the fake repository, the re-sign
  cut-over (path (a)) installed by `refresh --current`, then a routine
  proposal auto-approves against the adopted base.
- `test_publish_authority.py` / a new `test_publish_signer.py`: the
  publisher's signer steps with the client and aptly injected: legacy mode
  without the client config; expired repository; leftover `*.tmp`
  reported; `pending` exits 3 before consuming the approval; refused exits
  2; approved runs the switch with the stand-in `PATH`; refresh and live
  failures recorded with exit 2; the record's `signer` block; the proposal
  config file equals the live config plus the endpoint; the tool list.
- No aptly publish is run by the tests (the harness's fake aptly records
  its arguments). The end-to-end rehearsal on `/var/tmp/aptly-rehearsal`
  with the real aptly is May's/C's rehearsal allowance and is not part of
  this phase's verification; the -021 rehearsal already proved the aptly
  behaviour the publisher relies on.

## 9. Residual risks (stated)

- Content-based trust: a bad build of an established package that passes
  the gates is signed automatically (architecture section 4.4, accepted).
- The script-map rule compares against the signer's own record; content
  adopted without `.deb`s, or published before this phase, is never
  routine until one console-approved publication records its maps.
- The proposal publication copies the whole snapshot pool into `/var/tmp`
  for each publication (308 MB today; removed at the end). A run that
  dies before its cleanup leaves a `proposal-<task>` publication record in
  the live aptly database (visible in `publish list`, harmless; the next
  run of that task drops it).
- The `Contents` precondition is May's cut-over step; until it is done the
  signer refuses every Release, which fails closed.
- Legacy mode is chosen by the presence of May's client configuration in
  a trusted directory; during the rotation window a publication under the
  local key is possible by removing that file and is visible only in the
  record (`signer.mode: legacy`). The window ends when the old key leaves
  builder.
- The adopted content is taken from the repository as served; May's
  reading of the summary is the check.

## 10. Runbook for May (cut-over, outline; the detailed steps stay his)

1. Signer VM: install `signer/`, `policy.json`, the template; `console
   init`; generate the key; the keyring with the public key; the vbox
   `never_allowed` entry.
2. builder: `~/.config/aptly-signer/standin.json` and `client.json`
   (May's files); republish the live distribution with `-skip-contents`
   under the local key.
3. Signer: `console adopt-live`, type `adopt`.
4. The cut-over under the new key, May's choice of two paths, both his
   by rule 11: (a) `resign` on the signer, then `scripts/signer_client.py
   refresh --task cadence --current` on builder: the adopted content is
   served under the new key with no package change; `apt update` on both
   targets verifies it; or (b) the first package publication through
   `publish_aptly.py`, which rule 11 sends to the console, where May
   approves it. After either, routine proposals are automatic.
5. The cadence timers (builder and signer), installed last: a timer-driven
   `resign` on the signer sets `current` just as May's manual one does, so
   the timers come only after the cut-over. Then the rotation per -019.

## 11. Design Challenger round 1: REVISE, and the consolidated revision

Findings taken (the Challenger's ids): **B1** (blocking) the idempotent
lookup returns only a pending proposal or an unused approval on the
current base; a signed-but-not-live approval leads to a new proposal that
rule 9 routes to the console. **S1** an added row without a map read in
this proposal is not routine. **S2** rule 11. **S3** `/live` runs after a
failed refresh; manual `signer_client.py live` as recovery. **S4** legacy
mode in the record and in the residual risks. **S5** endpoint per task; a
rerun republishes. **S6** `resign` after `adopt-live` works on the stored
files (the cut-over path (a)). **S7** rule 4's same-source check. **N1**
absent Valid-Until passes. **N2** the message is the signal. **N3** the
pool copy size stated. **N4** architectures from the live Release. **N5,
N6, N11** stated consequences. **N7** fetch order. **N8** client keys
listed and validated. **N10** `-skip-contents` on the switch. **N12**
linger and the signer's timer. Not taken: verifying the served InRelease
with the old public key at `adopt-live` (May reads the summary; the old
key is on its way out). Round 2 asked on this revision.
