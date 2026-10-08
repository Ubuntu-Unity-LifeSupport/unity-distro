# UNITY-20261008-004: one canonical repository database backup script

Task kind: tool. Owner: A. Parent: UNITY-20260929-009.

## 1. Problem

Before `repo add`, each publication backs up the live repository database
(`docs/ENGINEERING-PROCESS.md` section 6, step 3). There is no script for
this in `scripts/`. Instead, six tasks each copied `tools/backup-db.py` from
the previous one:

- UNITY-20260927-012
- UNITY-20260927-040
- UNITY-20260928-019
- UNITY-20260928-022
- UNITY-20261002-002
- UNITY-20261002-003

Measured on main: the six copies are identical after their docstrings
(`diff` of each against the -003 copy, docstring lines left out). They
differ only in the header that names the task, not in what they do. The
earlier statement that they "diverged" meant those headers.

All copies share three flaws:

1. **A mismatch exits 0.** When the copy differs from the live db, the
   script prints `equal to live: False` and exits with code 0. Nothing
   stops the next step.
2. **Nothing records where and when the backup was taken,** apart from
   the printed line.
3. **The live path is fixed,** so the script cannot be tested without the
   live repository.

## 2. Existing fix

None in `scripts/`. Result: `NOT_FIXED`. Issue search: `NOT_FOUND`
(internal tool).

## 3. Change

**Scope.** The script copies `db/` only, which covers steps 3 and 5 of
section 6:
- `repo add`, `repo remove` and `snapshot drop` change only `db/`;
- the pool files they leave become orphans.

The replacement in UNITY-20260927-021 also backed up only `db/`. This is
not a backup for `publish switch` or `db cleanup`, which change `public/`
and the pool. The full restore in UNITY-20260927-047 R8b needed `public/`
too.

New script `scripts/backup_aptly_db.py [BACKUP_DIR] [--task ID]`.

**Lock.** The script opens `<live>/db/LOCK` read-only and takes
`flock(LOCK_SH | LOCK_NB)`. It holds the lock until the second read of the
live db is done. Measured in a scratch root (`runs/00-lock-behaviour.txt`):
- A writing call, `repo create`, was started while we held the shared lock.
  After 3 s it was still waiting, and the files under `db/` were
  unchanged. The same call finished by itself with rc 0 about 6 s after
  the release. The tool retries with a pause.
- `serve` does not hold the lock between requests.

So a busy lock means a tool is working on the db right now, and the
script refuses.

**Refusals.** The script exits 2 and creates no directory when:
- the live `db/` or its `LOCK` is missing;
- the lock is busy;
- a repository tool process is running (`pidof aptly`; a missing `pidof`
  also refuses);
- `BACKUP_DIR` exists, or its resolved path lies inside the resolved live
  root.

**Steps.**
1. With umask 077, create `BACKUP_DIR` (mode 0700) and run `cp -a
   <live>/db <BACKUP_DIR>/db`. If `cp` fails, write `backup.json` with
   `complete: false` and exit 1.
2. Write the sha256 list of every file of the copy to `db.sha256`, one
   line per file (`<sha256>  db/<path>`). Empty files such as `LOCK` and
   `*.log` are included.
3. Read the live `db/` again and compare.
4. Write `backup.json` with:
   - `live`, `task` and `created_at` (UTC);
   - `files` and `list_sha256`;
   - `complete` and `equal_to_live`.
5. Print the path and the summary.

**Exit codes.** 0 only if the copy is complete and equal to the live db. 1
for a copy that is incomplete or differs, which is left in place for
inspection. 2 for a refusal.

**Default `BACKUP_DIR`.** `~/backups/<task or "aptly-db">-<UTC stamp>`.
The command guard admits the call; it denies a path that ends in
`/aptly`.

**`--live PATH`.** Default `/srv/aptly`. It is marked in its help text as
a test option, and section 6 does not show it.

**Documentation.** `docs/ENGINEERING-PROCESS.md` section 6, step 3 points
to the script and states the scope. The examples gain the call. The six
old copies and their cards stay as they are.

**Tests.** `scripts/tests/test_backup_aptly_db.py` uses scratch live roots
only and fake binaries placed first in `PATH`. No hook goes into the
script. The cases:
- a good copy: the list (with empty files), `backup.json`, modes 0700,
  exit 0;
- the lock held by the test: exit 2, no directory created;
- a running process reported by a fake `pidof`, and a missing `pidof`;
- an existing `BACKUP_DIR`; a `BACKUP_DIR` inside the live root, directly
  and through a symlink; a symlinked live root;
- a missing live `db/` or `LOCK`;
- a fake `cp` that copies and then changes the live db: exit 1,
  `equal_to_live: false`;
- a fake `cp` that fails: exit 1, `complete: false`;
- the default directory name with `--task`.

`scripts/tests/test_command_guard.py` gets a test that the guard admits
the call.

## 4. Verification plan

- The whole `scripts/tests` suite passes.
- One read-only run against the live `/srv/aptly` into a scratch directory
  under `~/backups/`, only with C's OK and while no publication slot is
  open. It reads the db and writes only the backup. Its summary goes into
  `runs/01-live-backup.txt`.
- Mutations:
  - exit 0 on a mismatch;
  - skip the `pidof` check;
  - drop the flock;
  - allow an existing `BACKUP_DIR`.

## 5. Design review

The Design Challenger, a temporary subagent, reviewed the design in two
rounds.
- **Round 1: REVISE.** It required four changes:
  1. a shared flock on `db/LOCK` for the copy and the comparison;
  2. tests with fake `cp`/`pidof` instead of a hook in the script, plus
     cases for the lock, a symlink, a failed `cp` and empty files;
  3. a guard test;
  4. the scope (`db/` only) stated.
- **Round 2: APPROVE.** It asked that the lock measurement use one writing
  call that stays alive across the release. That was done:
  `runs/00-lock-behaviour.txt`.

## 6. Finding

All six old copies exit 0 when the copy differs from the live db. They
print `equal to live: False` and stop there, so nothing prevents the
`repo add` that follows. The canonical script exits 1 in that case.

Recorded outputs show `equal to live: True` for:
- UNITY-20260927-040 (`runs/db-backup.txt`);
- UNITY-20260927-021 (`logs/11-replace-step0.txt`);
- UNITY-20260928-019 (`runs/11-db-backup.txt`).

The cards of the following tasks record at most the backup path, not the
script's result:
- UNITY-20260927-012
- UNITY-20260928-022
- UNITY-20261002-002
- UNITY-20261002-003

Their results cannot be checked now, because the live db has changed
since then.

## 7. Results (branch `a/UNITY-20261008-004`)

- **`runs/00-lock-behaviour.txt`.** This was a scratch root, never `/srv`.
  A `repo create` started under our shared lock was still waiting after
  3 s, and the files under `db/` were unchanged. The same call finished
  with rc 0 about 6 s after the release. An idle `serve` holds no lock.
- **`runs/01-live-backup.txt`.** C approved one run, with the slot closed
  and no repository tool running. The results:
  - rc 0;
  - the backup is `~/backups/UNITY-20261008-004-20261008T050534Z` (mode
    0700), with 17 files and `complete: true`, `equal_to_live: true`;
  - `db.sha256` equals the live db listed again afterwards;
  - the newest db file is the same before and after (03:15:51Z);
  - no file under the live root changed, appeared or disappeared, judged
    by the full list with size and mtime taken before and after.
- **`runs/02-suite.txt`.** `scripts/tests` gives 339 passed, 1 skipped and
  684 subtests passed. That includes the 13 tests in
  `test_backup_aptly_db.py` and the guard admitting the two calls.
- **`runs/03-mutations.txt`.** Each mutation was made in a scratch copy of
  `scripts/`, and each was caught:

  | Mutation | Result |
  |---|---|
  | exit 0 on a mismatch | 2 tests fail |
  | `pidof` check skipped | caught |
  | flock dropped | 3 tests fail |
  | lock released before the second read | `test_lock_held_through_the_second_read` fails |
  | existing `BACKUP_DIR` allowed | caught |
  | inside-live check skipped | caught |

  The test for the early release was added after its mutation first
  survived. It passed 5 times out of 5 on the code and failed 5 times out
  of 5 on the mutation.
