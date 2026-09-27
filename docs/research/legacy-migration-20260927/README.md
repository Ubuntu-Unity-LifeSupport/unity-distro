# Legacy migration 2026-09-27 (process bootstrap)

One-off reconciliation of all work done before `ENGINEERING-PROCESS.md`
took effect. Read-only: no package code changed, nothing built for release,
nothing published, no VM rolled back. Historical results are NOT presented as
results of the new pipeline.

- Agent A's zone: [A.md](A.md) - 45 items (A-L01..A-L45).
- Agent B's zone: [B.md](B.md) - 57 items (B-L01..B-L57).
- Coordinator's zone: 2 items (reply draft to the gtk-nocsd maintainer,
  upstream queue) - kept in the coordinator's private notes.

## Counts

| | A | B | C | total |
|---|---|---|---|---|
| LEGACY_VERIFIED | 11 | 18 | 0 | 29 |
| LEGACY_PARTIAL | 7 | 15 | 2 | 24 |
| REQUIRES_REVALIDATION | 15 | 10 | 0 | 25 |
| SUPERSEDED | 12 | 14 | 0 | 26 |
| items | 45 | 57 | 2 | 104 |

Rule applied: any fix whose root cause is unproven, whose test is unreliable,
or whose patch may be broader than needed or in the wrong layer is
REQUIRES_REVALIDATION, never VERIFIED or PARTIAL.

## New tasks

38 tasks `UNITY-20260927-001` .. `-038`, all `BACKLOG`, unassigned, created
through `scripts/taskctl.py`. Each names its legacy item. Nothing started.

## Evidence gaps

- Every published version (38 source packages in aptly) predates the release
  gate: no build manifest, gate, version-safety record, aptly snapshot or
  publish record. Not republished just to create records.
- Several published packages have no source package in aptly, or a binary-only
  older version; some sources live only as exported patches
  (`docs/package-patches-b/`).
- unity-lens-files +unity1: the exact source that produced the published binary
  is lost; the source in aptly is a regeneration.
- Defects found during the reconciliation are listed as tasks, not fixed here.
