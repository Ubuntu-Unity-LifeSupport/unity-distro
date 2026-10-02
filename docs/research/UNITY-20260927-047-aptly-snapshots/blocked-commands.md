# UNITY-20260927-047: the exact phase R commands

**Correction (2026-09-28).** The previous version of this file (55461b9,
2026-09-27) wrote every phase R command as `aptly -config=$S/aptly.conf
publish …` with a scratchpad config. That form got past the command guard
only because of the bypass B had itself reported (UNITY-20260927-058), so the
list asked for permission to use a bypass. It was never run. The guard now
has the narrow rehearsal allowance of UNITY-20260927-057 and section 6 of
ENGINEERING-PROCESS, and phase R uses that allowance. Phase L was not
authorized on 2026-09-28; on 2026-09-29 May gave its GO, and it now runs
through the live-phase allowance of UNITY-20260929-008 (section "Phase L"
below).

## Setup (done 2026-09-28, `prepare-rehearsal.py`, `logs/20-rehearsal-root.txt`)

- `/var/tmp/aptly-rehearsal` (0700, claude) with `aptly.conf`: the live
  values, `rootDir` = `/var/tmp/aptly-rehearsal/state`.
- `incoming/` holds 333 files, copied by reading /srv/aptly with sha256
  checked. They are the repository's 285 package records: 258 binaries from
  the published Packages index and 27 source packages with 48 files. There
  are no links into /srv/aptly. /srv/aptly itself is unchanged (sha256 list
  before and after, 633 files).
- The rehearsal database is **fresh** (057's requirement): aptly creates it
  with the first command below. The live db is not copied.

## Commands

C = `/usr/bin/aptly -config=/var/tmp/aptly-rehearsal/aptly.conf`, K =
`-gpg-key=7BF3F77FC27B152C`, T = `/var/tmp/aptly-rehearsal`.

After **every** aptly command: `chmod -R go-w T`. The Bash tool runs with
umask 0002, aptly creates directories 0775, and the guard's tree check
denies a group-writable directory.

All commands are plain: no quoting. `-origin`/`-label` are not needed,
because aptly's default Origin and Label for prefix `.` and distribution
`resolute` are exactly `. resolute`, as live.

```sh
# R1 - the scratch repository from the same package files
C repo create -distribution=resolute -component=main unity-resolute
C repo add unity-resolute T/incoming
# check: repo keys = live (285: 258 binaries = published Packages, 27 sources)

# R2 - publish it like live, compare with /srv/aptly/public
C publish repo -distribution=resolute -architectures=amd64 K -batch unity-resolute
C publish show resolute

# snapshot for R3/R5
C snapshot create unity-resolute-20260927-047 from repo unity-resolute

# R3 - aptly refuses to switch a repo publication (expected failure)
C publish switch resolute unity-resolute-20260927-047

# R4 - backup of state/public and state/db to T/backup-r4 (cp -a, sha256 list)

# R5 - snapshot publication at prefix candidate
C publish snapshot -distribution=resolute -architectures=amd64 K -batch unity-resolute-20260927-047 candidate
C publish show resolute candidate

# R6 - drop and republish the snapshot at . (timed gap)
C publish drop resolute
C publish snapshot -distribution=resolute -architectures=amd64 K -batch unity-resolute-20260927-047
C publish show resolute
# check: files vs R2 (only Date, InRelease, Release.gpg differ); isolated apt
# client on T/state/public (Signed-By the key): update without E/W

# R7 - switch as publish_aptly.py does, without -gpg-key
C snapshot create unity-resolute-20260927-047b from repo unity-resolute
C publish switch resolute unity-resolute-20260927-047b
# check: signed by 29A893E0...C27B152C

# R8a - rollback by republishing the repo
C publish drop resolute
C publish repo -distribution=resolute -architectures=amd64 K -batch unity-resolute

# R9 - drop candidate: only state/public/candidate goes (before R8b: the R4
# backup predates candidate, so after the restore there is none to drop)
C publish drop resolute candidate
C publish list

# R8b - rollback by restoring the R4 backup (mv aside, cp -a, sha256 compare), then
C publish list
```

**Order corrected (2026-09-28).** In the first run R9 had to be run before
R8b, because the R4 backup predates `candidate`. The list above now has that
order; the commands are unchanged. The first run (logs/31) is preliminary
and not counted (May): B's session had no command guard. Before a repeat,
the state from the first run has to be reset. The repeat must start from
the prepared root (aptly.conf and incoming only), which is the root with
`state/`, `backup-r4/`, `aside-r8b/` and `backup-r4.sha256` moved aside.
That reset is part of the repeat and is done only after UNITY-20260928-012.

Every `publish` command above is allowed only while C's marker
`~/coordinator/rehearsal-authorization.json` is valid (May's separate GO).
The other aptly commands (repo, snapshot) work on the rehearsal config under
the 058 rules.

## Phase L (live) - plan v2, 2026-09-29: B runs every command (UNITY-20260929-008)

Not executed. It needs May's GO for the run and his window, the L0 record,
and then C's live marker. Before the window, no live command, no backup,
and nothing that opens the live database: in the 2026-09-28 13:09Z event,
opening it rewrote leveldb files.

**Actors.**

- **B**: L0, every aptly command below and every check, and the L5b restore.
- **A**: the before/after captures on target (C asks A).
- **C**: declares the freeze, writes the live marker after the L0 record,
  and removes it afterwards.
- **May**: gives the GO and the window.

**Guard.** The eight live `publish` strings are admitted by
UNITY-20260929-008 only exactly as in
`/home/claude/unity-distro/.claude/hooks/live-commands.json` (list sha256
`4e9dde5a5b862f58a27f47bfaea80942fab73c46ac0b9434a0c0d6e70f42294a`). Each
must be one foreground Bash call; no batching, no background. Every
admission adds one line to `~/coordinator/live-log.jsonl`. The
non-publish commands (repo/snapshot) pass under the 058 rules. They are
written with the same `-config`, and they open the live database, so they
run only inside the window.

The eight strings, numbered as below:

```
P1  /usr/bin/aptly -config=/home/claude/.aptly.conf publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047 candidate
P2  /usr/bin/aptly -config=/home/claude/.aptly.conf publish show resolute candidate
P3  /usr/bin/aptly -config=/home/claude/.aptly.conf publish drop resolute
P4  /usr/bin/aptly -config=/home/claude/.aptly.conf publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047
P5  /usr/bin/aptly -config=/home/claude/.aptly.conf publish show resolute
P6  /usr/bin/aptly -config=/home/claude/.aptly.conf publish repo -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute
P7  /usr/bin/aptly -config=/home/claude/.aptly.conf publish list
P8  /usr/bin/aptly -config=/home/claude/.aptly.conf publish drop resolute candidate
```

### L0 - preflight and backup (B), after the GO, before the marker

Each item goes into the L0 record `logs/44-phase-L-L0.txt`, which the marker
cites:

1. C has declared the freeze in the coordinator log: no aptly and no
   `publish_aptly.py` by anyone from the backup to DONE. A is informed.
2. Builder: no `aptly`, `apt`, `apt-get`, `dpkg` or `unattended-upgrade`
   process (`pidof`).
3. Guard:
   - `install_command_guard.py --check` is OK;
   - the `pgrep -f` probe is denied;
   - the list sha256 is `4e9dde5a...`;
   - `live-proof.py <B session>` with no marker gives 8x "no live
     authorization" (payloads only).
4. Pinned config and binary:
   - `~/.aptly.conf` is mode 644, owned by claude, with sha256
     `ece05ab8ad8469cdeaa39487013830d7a9304cc09cf9989a18543193d8831b25`;
   - `/usr/bin/aptly` is root-owned;
   - secret key `7BF3F77FC27B152C` is present (`gpg --list-secret-keys`).
5. target2 (B):
   - `touch ~/.dirty`;
   - add our source (`/etc/apt/sources.list.d/unity-distro.sources`: URIs
     `http://192.168.56.10:8080/`, Suites resolute, Components main,
     Architectures amd64, Signed-By `/etc/apt/keyrings/unity-distro.asc`
     from `http://192.168.56.10:8080/unity-distro-archive.asc`);
   - `client-capture.sh before-L our-binary-names.txt` into
     `logs/45-target2-before-L.txt`;
   - then stop `apt-daily.timer` and `apt-daily-upgrade.timer` for the
     window.
6. target (A): `client-capture.sh before-L` on A's machine, and the timers
   not within 30 minutes of the window. C asks A and puts the file name in
   the record.
7. Backup (B, no aptly process; file copies do not open the database):
   - `cp -a /srv/aptly/db /srv/aptly/public` into
     `~/backups/aptly-047-L-<UTC>/`;
   - a sha256 list of both copies, plus that list's sha256;
   - `live-list.py` over all of /srv/aptly (list and sha256) as the
     baseline.
8. The record ends with its own UTC time and the commit that holds it. C
   writes `~/coordinator/live-authorization.json` with:
   - kind `live-publish`;
   - session_id of B;
   - a window of at most 6 hours;
   - `commands_sha256` `4e9dde5a...`;
   - a reference naming May's GO and this record.

### In the window (B), one command per call, in this order

```sh
# L1 - the snapshot (058 rules, not in the live list)
aptly -config=/home/claude/.aptly.conf repo show unity-resolute                       # 285 packages
aptly -config=/home/claude/.aptly.conf snapshot list -raw                             # no unity-resolute-20260927-047
aptly -config=/home/claude/.aptly.conf snapshot create unity-resolute-20260927-047 from repo unity-resolute
aptly -config=/home/claude/.aptly.conf snapshot show unity-resolute-20260927-047      # 285 packages

# L2 - candidate
P1
P2                                   # Prefix candidate / unity-resolute-20260927-047 [snapshot]
# check: public/candidate/dists/resolute vs public/dists/resolute - no
#   file-set or index difference; Release differs only in Date/Label/Origin
#   (and the checksums through binary-amd64/Release); signer 29A893E0...C27B152C

# L3 - switch . to the snapshot (record UTC just before P3; gap = new InRelease mtime - that; R6 <= 1.16 s)
P3
P4

# L4 - checks
P5                                   # main: unity-resolute-20260927-047 [snapshot]
# public/dists/resolute vs the backup's: only Date, InRelease, Release.gpg
#   differ; signer 29A893E0...C27B152C; pool 258/258 names
# isolated apt client on file:/srv/aptly/public, Signed-By the key: update with no E/W
# target2: client-capture.sh after-L -> logs/46, diff with logs/45 (only our Release Date)
# target (A): after-L, diff with before-L

# L6 - after L4 passes
P8
P7                                   # only ./resolute publishes {main: [unity-resolute-20260927-047]}
# live-list.py after: vs the baseline only db/ and public/ may differ, pool/ unchanged
# live-log.jsonl: one line per P command run, session B, marker sha
```

### L5 - rollback, only if an L4 check fails

- **L5b** (preferred; the only path if P4 itself failed). B checks that no
  aptly process is running, then:
  1. `mv /srv/aptly/db` and `/srv/aptly/public` aside into
     `~/backups/aptly-047-L-<UTC>/aside/` (kept, not deleted);
  2. `cp -a` the backup copies back;
  3. compare with the backup's sha256 list before any aptly command;
  4. then P7 (`./resolute publishes {main: [unity-resolute]}`) and
     `aptly -config=/home/claude/.aptly.conf repo show unity-resolute`.
- **L5a** (only if P4 succeeded and L5b is not wanted): P3, then P6, then P5.

After a rollback, P8 still removes `candidate` when it exists, then P7.

### After the window

- B reports all steps, the live-log lines and the live-list before/after to C.
- C removes the marker and records the end of the freeze.
- At -047's DONE: C removes the list from main (a separate commit), and
  UNITY-20260927-035 is told that the live snapshot is
  `unity-resolute-20260927-047`.
- B rolls target2 back to Clean-2, which also brings back its timers.

The 2026-09-29 version with May running commands in his terminal (a260d8d) is
superseded by this one.
