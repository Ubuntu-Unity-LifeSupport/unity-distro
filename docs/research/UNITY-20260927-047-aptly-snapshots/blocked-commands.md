# UNITY-20260927-047: the exact phase R commands

**Correction (2026-09-28).** The previous version of this file (55461b9,
2026-09-27) wrote every phase R command as `aptly -config=$S/aptly.conf
publish …` with a scratchpad config. That form got past the command guard
only because of the bypass B had itself reported (UNITY-20260927-058), so the
list asked for permission to use a bypass. It was never run. The guard now
has the narrow rehearsal allowance of UNITY-20260927-057 and section 6 of
ENGINEERING-PROCESS, and phase R uses that allowance. Phase L is not
authorized (May, 2026-09-28) and is not listed here any more; its earlier
form stays in git history.

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

## Phase L (live) - prepared 2026-09-29; GO from May relayed by C, not executed

Live aptly: `~/.aptly.conf` of user `claude` on builder, `rootDir` /srv/aptly,
no publish endpoints; signing key 7BF3F77FC27B152C (fingerprint
29A893E03970066F2DD287D47BF3F77FC27B152C) in claude's keyring. Commands use
that default config: no `-config`, plain words, one per line, no quoting.
Origin/Label are aptly's defaults (`. resolute`), which R2/R6 showed equal
live, so no `-origin`/`-label` (the 2026-09-27 draft had them).

**Who runs what.** The guard denies every live `publish` in an agent session;
its allowance covers only the rehearsal root, and it is not changed or worked
around. So:

- **May** runs, in his own terminal on builder as user `claude` (outside
  Claude Code), every live write through aptly: L1, L2, L3, L6 and the L5a
  rollback, plus the `publish show` / `publish list` reads.
- **B** runs the rest: preflight, backup, file comparisons, the target2
  captures, the L5b restore (mv/cp, no aptly process) and the non-publish
  aptly reads that the guard allows (`repo show`, `snapshot show`, `snapshot
  list`).
- **A** (or B with A's permission) captures target before/after.

B waits between steps for May's pasted output.

```sh
# L0 - preflight (B), immediately before L1; C has declared the write freeze
#   (no aptly and no publish_aptly.py by anyone from the backup to DONE)
#   - no aptly/apt/dpkg process on builder; none on target/target2
#   - not within 30 min of an apt timer on target (A) or target2; target2's
#     apt-daily*.timer stopped for the window (B's machine)
#   - target2: our source (http://192.168.56.10:8080/, Signed-By the
#     published key) added, then client-capture.sh before-L
#   - target: client-capture.sh before-L (A)
#   - backup: cp -a /srv/aptly/db and /srv/aptly/public into
#     ~/backups/aptly-047-L-<UTC>/ plus a sha256 list of both;
#     live-list.py baseline (all of /srv/aptly)
aptly repo show unity-resolute                       # B: 285 packages
aptly snapshot list -raw                             # B: no unity-resolute-20260927-047 yet

# L1 - the snapshot (May: a live db write)
aptly snapshot create unity-resolute-20260927-047 from repo unity-resolute
aptly snapshot show unity-resolute-20260927-047      # B: 285 packages = repo

# L2 - publish the snapshot at prefix candidate (May)
aptly publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047 candidate
aptly publish show resolute candidate                # May
# check (B): public/candidate vs public - no file-set/index difference;
#   Release differs only in Date/Label/Origin (+ checksums through
#   binary-amd64/Release), signed by 29A893E0...C27B152C

# L3 - switch . from the repo to the snapshot: drop, then at once republish (May)
#   (B records the UTC time right before; gap = new InRelease mtime - that;
#   rehearsal R6: <= 1.16 s)
aptly publish drop resolute
aptly publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047

# L4 - checks
aptly publish show resolute                          # May: main: unity-resolute-20260927-047 [snapshot]
# B: public/dists/resolute vs the backup's - only Date, InRelease,
#   Release.gpg differ; pool 258/258; isolated apt client on
#   file:/srv/aptly/public (Signed-By the key): update with no E/W,
#   same candidates; target2 client-capture.sh after-L, diff with before-L
# A: target after-L, diff with before-L

# L5 - rollback, only if an L4 check fails
# L5b (preferred; the only path if L3's republish itself failed) - B, no
#   aptly process: mv /srv/aptly/db and /srv/aptly/public aside into
#   ~/backups/aptly-047-L-<UTC>/aside/, cp -a the backup back, compare the
#   sha256 list before any aptly command; then:
aptly repo show unity-resolute                       # B
aptly publish list                                   # May: ./resolute publishes {main: [unity-resolute]}
# L5a (only if L3 succeeded and L5b is not wanted) - May:
aptly publish drop resolute
aptly publish repo -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute

# L6 - after L4 passes: drop candidate (May)
aptly publish drop resolute candidate
aptly publish list                                   # May: only ./resolute, the snapshot
# B: live-list.py after; only db/ and public/ may differ from the baseline,
#   pool/ unchanged; tell UNITY-20260927-035 the live snapshot is
#   unity-resolute-20260927-047
```
