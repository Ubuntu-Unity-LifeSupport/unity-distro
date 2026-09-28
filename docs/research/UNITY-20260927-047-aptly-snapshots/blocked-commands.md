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
# R8b - rollback by restoring the R4 backup (mv aside, cp -a, sha256 compare), then
C publish list

# R9 - drop candidate: only state/public/candidate goes
C publish drop resolute candidate
C publish list
```

Every `publish` command above is allowed only while C's marker
`~/coordinator/rehearsal-authorization.json` is valid (May's separate GO).
The other aptly commands (repo, snapshot) work on the rehearsal config under
the 058 rules.
