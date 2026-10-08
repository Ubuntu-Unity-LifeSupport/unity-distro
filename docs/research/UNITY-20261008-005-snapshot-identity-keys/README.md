# UNITY-20261008-005: the apt view identifies the snapshot by aptly keys, not names

Task kind: tool. Owner: A. Parent: UNITY-20261008-002 (follow-up recorded in
its card, section 3).

## 1. Problem

`scripts/apt_view.py` records the gated snapshot's identity as
`snapshot.list_sha256`, a hash of the `snapshot show -with-packages` lines,
which have the form `<Package>_<Version>_<Arch>`. `publish_aptly.py`
(`compare_views`) refuses a switch-time view whose `list_sha256` differs
from the gate-time one.

The names carry no bytes. Suppose the snapshot is dropped and recreated
under the same name between the gate and the switch, with the same names
and versions but other bytes. The view does not notice.
`check_gated_snapshot` (UNITY-20261008-002) checks the bytes of this build's
artifacts at the switch, but every other package in the snapshot is
covered only by names.

## 2. Reproduction

`tools/repro.py` runs in a scratch root with its own `-config`
(`runs/01-repro-main.txt`):
1. snapshot `unity-resolute-20990101-001` holds `demo-bin 1.0+unity1`;
2. the snapshot is dropped and recreated under the same name with a
   `demo-bin 1.0+unity1` of other bytes.

Results:
- `snapshot_model` lists the same names, so `list_sha256` is equal before
  and after.
- The aptly keys differ: `Pamd64 demo-bin 1.0+unity1 d4e45b0ff0f89376`
  before, `Pamd64 demo-bin 1.0+unity1 42f34e826438753e` after. The last
  field is aptly's hash of the package's files.

## 3. Existing fix

None. Result: `NOT_FIXED`. Issue search: `NOT_FOUND` (internal tool).

## 4. Change

1. **`apt_view.py`: new `snapshot_content(config, snapshot)`.** The full
   view records its result as `snapshot.content_sha256`. It is the sha256
   of a sorted list with one entry per package of the snapshot:
   - **Binary packages** (`.deb`, `.ddeb`, `.udeb`): `<aptly key>|<SHA256>`.
     These come from `snapshot search -format '{{.Key}}|{{index .
     "SHA256"}}' <snapshot> 'Name (% *)'`, keeping only the records whose
     key does not start with `Psource`. The query `Name (% *)` matches
     every package, including source records and a package literally
     named `name`. This was measured by the Design Challenger on 426
     records in a scratch root.
   - **Source packages**: `<aptly key>|<Checksums-Sha256 entries sorted
     and joined>`. These come from a second query, `snapshot search
     -format '{{.Key}}{{"\n"}}{{index . "Checksums-Sha256"}}' <snapshot>
     '$Architecture (source)'`, whose output is parsed in blocks per key.
     The field spans several lines, so it cannot share a line with the key.
   - The second query runs only when the first one returns `Psource` keys.
     On a snapshot with no source records, aptly's search exits 1 ("no
     results"), so it is skipped, as in the debs-only fixture of
     `test_version_safety.py`.
   - The `Psource` keys of the first query must be exactly the keys parsed
     from the second, or the view is refused. This catches parsing errors
     and a snapshot that changed between the two calls.
   - Blocks split on lines that do not start with whitespace.
   - A binary record with an empty `SHA256` is refused, and so is a source
     block without `Checksums-Sha256` lines.
   - So every package carries a sha256 of its own files: the `.deb` for
     binaries, the `.dsc` and its files for sources. Aptly's 64-bit files
     hash in the key is no longer the only link.
   - An empty snapshot makes the search exit 1 ("no results"), and
     apt_view raises on that. This fails closed.
   - `list_sha256` stays for display.
2. **`publish_aptly.compare_views`.** It requires `content_sha256`, present
   and equal, as well as `list_sha256`. A gate view without the field is
   refused, and the message says to regenerate the gate.
3. **`create_release_gate.py`.** It refuses a `version_check` view whose
   `content_sha256` is missing or empty.
4. **`version_safety` is unchanged.** The SAFE verdict does not depend on
   the new field.
5. **Tests.**
   - `scripts/tests/test_version_safety.py`: `CompareViewsTest.base` gets
     the field. `test_other_snapshot_content` gets a case where only
     `content_sha256` differs, and a case where it is missing at gate
     time.
   - A new integration test in a scratch root. The snapshot is recreated
     under the same name in two ways: a binary with other bytes, and a
     source with other bytes. In both cases `content_sha256` differs while
     `list_sha256` stays equal. The query pins `Name (% *)` against a
     package named `name`.
   - The gate refuses a view with the field missing or empty.
6. **`docs/ENGINEERING-PROCESS.md` section 6.** The version-safety
   paragraph says that the view identifies the snapshot's content by aptly
   keys and per-package sha256, not by names.

## 5. Verification plan

- `tools/repro.py` on the branch shows `content_sha256` differing.
- The whole `scripts/tests` suite passes.
- Mutations:
  - compare `list_sha256` only;
  - drop the SHA256 part of the line;
  - accept a missing field.

## 6. Design review

The Design Challenger, a temporary subagent, reviewed the design in three
rounds.
- **Round 1: REVISE.** It required:
  - the unambiguous query `Name (% *)`;
  - the sources' `Checksums-Sha256`;
  - the field added to `CompareViewsTest.base`;
  - the repro quote corrected.
- **Round 2: REVISE.** It required:
  - skipping the second query on a snapshot without sources;
  - checking that both queries return the same source keys;
  - refusing empty hashes.
- **Round 3: APPROVE.**

## 7. Results (branch `a/UNITY-20261008-005`)

- **Before the change, `runs/01-repro-main.txt`.** The snapshot was
  recreated under the same name with a deb of other bytes. The names, and
  so `list_sha256`, stay equal, while the aptly keys differ.
- **After the change, `runs/02-repro-branch.txt`.** In the same case
  `snapshot_content`, the input of `content_sha256`, differs.
- **New tests, `scripts/tests/test_apt_view_snapshot_content.py`.** There
  are 9 tests.
  - Unit tests with a fake `aptly()`:
    - the lines produced;
    - no second search when there are no sources;
    - an empty SHA256 is refused;
    - a source without checksums is refused;
    - source keys that differ between the two searches are refused.
  - Scratch-root tests:
    - a binary recreated with other bytes;
    - a source recreated with other bytes;
    - a 3.0 (quilt) source lists its three files, with the `.dsc` sha256
      checked;
    - the query matches every record, including a package named `name`;
    - a snapshot with debs only.
- **`test_version_safety.py`.**
  - `CompareViewsTest.base` has the field.
  - New: same names with other content, refused.
  - New: a gate view without the field or with it empty, refused.
  - The debs-only full-view test is unchanged and passes.
- **`test_build_dependencies_consumers.py`.** The real gate refuses a
  `version_check` view whose `content_sha256` is missing or empty. With the
  field present, it goes on to the next check.
- **`runs/03-suite.txt`.** `scripts/tests` gives 352 passed and 1 skipped.
- **`runs/04-mutations.txt`.** Each mutation was made in a scratch copy of
  `scripts/`, and each was caught:
  - `list_sha256` compared alone;
  - a missing field accepted;
  - the binary SHA256 dropped;
  - the source checksums dropped;
  - the key cross-check skipped;
  - a lowercase `name` query;
  - the lines left unsorted;
  - the gate check removed.
