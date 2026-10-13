# UNITY-20261008-002: publish_aptly.py checks binary bytes in the gated snapshot

Task kind: tool. Owner: A. Parent: UNITY-20260929-009.

## 1. Reproduction

Before the switch, `publish_aptly.py` (main `c672ce9`) checks the gated
snapshot in two ways:
- it looks for each expected `<Package>_<Version>_<Architecture>` in
  `aptly snapshot show -with-packages`;
- it compares the source package's `Checksums-Sha256` with the `.dsc` and
  its files (`source_package_matches`).

Nothing compares a binary's bytes with the manifest's sha256. A record with
the same name and version but other bytes therefore passes. That happens
when the repository holds an earlier build of the same version. It was
caught only by hand in UNITY-20260927-021 (`pool-check.py`) and in
UNITY-20261002-003 (comparing each pool file's sha256 with the manifest).

`tools/repro.py` builds a scratch aptly root, with its own `-config` and
never the live repository. It adds the source and a `demo-bin` with the
same version but other bytes than the manifest's, creates a snapshot, and
runs today's checks on it (`runs/01-repro-main.txt`):

```text
manifest demo-bin sha256 79b833507585 | in repository b958c3dc2fed
name check: pass | source check: pass
snapshot demo-bin SHA256 field: ['b958c3dc2fed'] | equals manifest: False
RESULT (checks of main c672ce9): ACCEPTED
```

The snapshot's `SHA256` field gives the bytes that are really there.
`taskctl.py` has read that field since UNITY-20260929-015, to confirm a
live snapshot at `PUBLISHED`. The publisher does not.

## 2. Existing fix

None. The only binary sha256 check against a snapshot is
`taskctl.confirm_live_publication`, which runs after publication. Result:
`NOT_FIXED`. Issue search: `NOT_FOUND` (internal tool). Board task
UNITY-20261008-003 is related: it is about `published_by`, not about the
snapshot.

## 3. Root cause and invariant

Root cause: the snapshot contract in `publish_aptly.py` checks binaries by
key only. The byte check lives only in `taskctl.py`, and nothing shares it.

Invariant: before the switch, the gated snapshot holds every binary of the
manifest exactly once, with the manifest's sha256. It also holds exactly
one source package of this name and version, made of exactly the build's
`.dsc` and files. The publisher and `taskctl` apply the same function.

Out of scope, on purpose:
- **Other versions of the same binary names in the snapshot.** These are
  normal: UNITY-20261002-003's snapshot holds +unity1 to +unity10 next to
  +unity11. That apt picks the built version is the job of the version
  safety check, which runs at gate time and again just before the switch.
  It requires every built binary to be apt's candidate at its own version.
- **The snapshot being dropped and recreated** under the same name between
  this check and the switch. `apt_view`'s `list_sha256` hashes names only
  (`snapshot show -with-packages`), so the switch-time view would not
  notice. The window is a few seconds, and it needs someone to recreate
  the snapshot by hand. This is a candidate follow-up for C: hash aptly
  keys, which include the files hash.

## 4. Change

1. `publish_aptly.py` gets a new function, `snapshot_content(artifacts,
   snapshot, run=None)`, which returns `(missing, differing)`.
   - If `run` is None, the function uses `run_aptly`, looked up at call
     time so that tests can replace it.
   - What moves into it from `taskctl.confirm_live_publication` is only
     the part after the live snapshot has been found, in the same order:
     1. the binary queries, in artifact order: `snapshot search -format
        '{{index . "SHA256"}}' <snapshot> 'Name (p), Version (= v),
        Architecture (a)'`, which must return exactly one line, equal to
        the manifest's sha256. No line counts as missing, and another line
        or several lines count as differing;
     2. the `{{.Key}}` query for the source, which must return exactly one
        line;
     3. only then, the `Checksums-Sha256` query through
        `source_package_matches`.
   - The record-kind checks and the error message stay in `taskctl`.
2. `publish_aptly.py` gets a second new function,
   `check_gated_snapshot(snapshot, expected_names, artifacts,
   run=None)`. It holds `main()`'s snapshot block: the names in
   `snapshot show -with-packages`, then `snapshot_content`. It returns an
   error or None.
   - `main()` makes one call to it, in the same place as today: before
     the switch-time `apt_view.py`, before `log_event("START"` and before
     the switch.
   - New refusal: `aptly snapshot <s> does not hold the build's artifacts:
     missing [...], other sha256 [...]`.
   - This also brings the source-key count to the publisher.
3. `taskctl.confirm_live_publication` calls `snapshot_content`. Its import
   stays lazy, inside the function. Its messages, behaviour and call order
   are unchanged. `scripts/tests/test_taskctl_live_snapshot.py` stays
   byte-for-byte as it is: its fake aptly asserts exact call lists.
4. Tests, in the new file `scripts/tests/test_publish_snapshot_content.py`:
   - Unit tests with a fake aptly, through `check_gated_snapshot`. Each case
     expects a result:
     - everything matches: accepted;
     - expected name missing in `snapshot show`: refused;
     - a binary of the same version with other bytes: refused;
     - a `.ddeb` with other bytes: refused;
     - a binary present twice: refused;
     - a binary missing in the search: refused;
     - the source missing: refused;
     - a source file with another hash: refused;
     - two source packages: refused.
   - Integration in a scratch aptly root with its own `-config`, as in
     `test_taskctl_live_snapshot.py`. The gated bytes are accepted. A
     rebuild of the same version is refused, with `demo-bin` under "other
     sha256".
   - Wiring, an `ast` test on `publish_aptly.main`. It checks that:
     - there is exactly one `check_gated_snapshot` call, and its result goes
       to `fail`;
     - the call comes before the `apt_view.py` call and before
       `log_event("START"`;
     - no `snapshot search` and no `source_package_matches` is left
       inline in `main()`.
5. `docs/ENGINEERING-PROCESS.md` section 6:
   - Step 5 stays **[process]** for the backup, `repo remove` and
     `snapshot drop`. Only its closing sentence on binary bytes becomes
     **[tool]**, with the new message.
   - In step 4, the pool check stays as an early check. A note says that
     the publisher now checks the bytes too.
   - In "Build manifest artifacts", the `.deb`/`.ddeb` bullet gets the
     sha256 rule.

## 5. Verification plan

- `tools/repro.py` against the branch: the result is refused, and
  `snapshot_content` names `demo-bin` under "other sha256".
- The new tests pass, and the whole `scripts/tests` suite passes,
  including the existing `test_taskctl_live_snapshot.py` unchanged.
- Mutation, on scratch copies:
  - if `main()` does not call `check_gated_snapshot`, the wiring test
    fails;
  - if `snapshot_content` compares names only, the bytes tests fail;
  - if the `{{.Key}}` count is removed, the two-sources test fails.

## 6. Design review

The Design Challenger, a temporary subagent, reviewed the design in two
rounds.

- **Round 1: REVISE**, with four required changes:
  1. state exactly which code moves, keep the import lazy, and leave the
     taskctl test file unchanged;
  2. add no rule against other versions of the same binary names, and
     write down why;
  3. add an `ast` wiring test;
  4. make the section 6 edits precise.
- **Round 2: APPROVE.**

One difference from the card: `check_gated_snapshot` takes no `package`
and `version` arguments, because the artifacts carry them.

## 7. Results (branch `a/UNITY-20261008-002`)

- **Before the change.** `runs/01-repro-main.txt` runs the scratch aptly
  root against `scripts/` of main `c672ce9`. A `demo-bin` with the same
  version but other bytes passes the name check and the source check:
  `ACCEPTED`.
- **After the change.** `runs/02-repro-branch.txt` runs the same case
  through `check_gated_snapshot`, which refuses it: "does not hold the
  build's artifacts: missing [], other sha256 ['demo-bin 1.0+unity1
  amd64']".
- **New tests.** `scripts/tests/test_publish_snapshot_content.py` has 16
  tests and all pass:
  - 12 unit tests with a fake aptly;
  - 3 `ast` wiring tests on `main()`;
  - 1 integration test in a scratch aptly root, which accepts the gated
    bytes and refuses a rebuild of the same version.
- **Full suite.** `runs/03-suite.txt`: `scripts/tests` gives 315 passed,
  1 skipped and 682 subtests passed. That includes
  `test_taskctl_live_snapshot.py`, which is unchanged, so its call-list
  assertions still hold.
- **Mutations.** `runs/04-mutations.txt`: each mutation was made in a
  scratch copy of `scripts/`.

  | Mutation | Result |
  |---|---|
  | None | 16 passed |
  | `check_gated_snapshot` call removed from `main()` | both wiring tests fail |
  | sha256 comparison removed (names only) | 4 bytes tests fail, the integration test among them |
  | key count weakened to "any key" | the two-source-packages test fails |

- **Section 6.** The following now say that the publisher checks binary
  bytes:
  - step 5, in its closing paragraph, which is **[tool]**;
  - the note on the pool check in step 4;
  - the `.deb`/`.ddeb` rule in "Build manifest artifacts".

## 8. Verification

An independent Verifier, a temporary subagent, checked `188e1b0`. Verdict:
**PASS**.

- On `scripts/` of main, a scratch aptly root accepts a `demo-bin` of the
  same version with other bytes. The branch refuses it. Every aptly call
  used the scratch `-config`.
- The moved code is identical to the removed taskctl body:
  - the same queries, order and message parts;
  - the import stays lazy;
  - the taskctl test file is unchanged.
- `main()` calls `check_gated_snapshot` exactly once and passes its result
  to `fail()`. The call comes before the switch-time `apt_view.py`, the
  `START` log line and the switch.
- Full suite: 315 passed and 1 skipped. The skip is unrelated (the live
  command list). The integration test ran.
- Five mutations of the Verifier's own were each caught:
  - the call removed;
  - names only;
  - the key count weakened;
  - "line contains the sha" accepted;
  - `.ddeb` skipped.
- The three edits to section 6 match the code.
- A scratch snapshot with these contents was accepted:
  - epoch versions;
  - an `Architecture: all` binary;
  - older versions of the same packages.

  A rebuilt arch-all `.deb` was refused.

Notes, none blocking:
- Section 1 now quotes the run on main as committed in
  `runs/01-repro-main.txt`.
- The follow-up on a snapshot dropped and recreated under the same name
  (section 3) is still open, and its ID comes from C.
