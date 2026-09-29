# UNITY-20260927-047 phase L - independent verification

## Round 1 (2026-09-29, ephemeral Verifier; branch tip 8b3e17d)

Verdict: **INCOMPLETE**, `REVIEWED`. The live operation was confirmed
independently. Two gaps are in the records.

Confirmed by the Verifier:

- InRelease and Release.gpg verify against the published key:
  - GOODSIG/VALIDSIG 29A893E0...C27B152C;
  - Release SHA256 lines match their files;
  - live dists vs the backup: same file set, index files byte-identical,
    only InRelease/Release/Release.gpg differ;
  - among Release fields only Date differs, Origin/Label are `. resolute`;
  - pool 258/258 equal.
- The live list now is byte-identical to logs/48b. Against 44b, only db/
  and public/dists/resolute/{InRelease,Release,Release.gpg} differ.
- The backup's sha list matches its 281 files, equals 44c and equals the
  pre-L db+public.
- live-log.jsonl:
  - 7 admitted lines (P1,P2,P3,P4,P5,P8,P7), all inside the window;
  - session, marker and list sha as recorded;
  - each string equals the removed list byte for byte;
  - the marker is absent.
- Target captures: only the header and Release Date differ; hashes match.
- Removal commit: 3 files; suite 158 OK / 1 skipped; the new test denies
  because the list is missing.
- The recorded gap is honest.

Gaps and what was done:

1. The evidence `authorization` still said "phase L not authorized". Fixed:
   approved_by May; reference names the GO for plan v2 cde32da (C,
   APTLY-FREEZE.md line 20, marker 61d806ab) and May's direct confirmation
   in B's session; scope names phase L (the eight listed strings plus L1,
   window, backup, rollback). peer_notice was updated.
2. The second guard false positive was not recorded: the inline `python3
   -c` with the publish word and `$S` after L6. It is now added to logs/47.

Missing proof it named:

- "No other aptly command between the backup and L1" was inferred. Now it
  is shown: logs/50 (`db-opens.py`, read-only) lists every goleveldb
  `db@open` in `/srv/aptly/db/LOG`. On 2026-09-29 there are exactly 11: the
  4 L1 commands (14:23:12-25Z) and the 7 P commands. None falls between the
  backup (14:21:17Z) and L1. The previous open is 2026-09-28 13:09:08.
- That the db holds the snapshot rests on the P5/P7 outputs in logs/47
  (leveldb is compressed). The goleveldb LOG shows a memdb flush at
  14:26:20. The live Release and Packages are consistent with it.

Remarks and what was done:

- The new test now also checks the specific reason (the list path in the
  message).
- The README phase L step 3 mentioned `-origin`/`-label` through "exactly
  as in R6". It is now clarified: the executed strings are those of plan
  v2.
- The empty `public/candidate/` directory is recorded.
- L1 is not in live-log, by design.
