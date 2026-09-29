# UNITY-20260927-036: record corrections after the legacy migration

Owner: agent B. Documentation only: the stale records listed in
`docs/research/legacy-migration-20260927/B.md` ("Unfinished work", item 12)
get a dated correction next to them; the original text is not rewritten.
Facts checked on 2026-09-27 (`logs/01-facts.txt`: aptly searches, rmadison,
package branches).

| record | stale statement | correction (where) |
|---|---|---|
| `docs/PATCHES.md:64` | libindicator +unity1 "not in aptly" | in aptly, superseded by +unity2 - appended section "Record corrections, 2026-09-27" (main `1232851`, via `append_record.py`) |
| `docs/PATCHES.md` | no row for unity-lens-files +unity1 | row added in the same appended section |
| `docs/status/B.md` (rebuild-trial paragraph) | libindicator +unity1 "built, not in aptly" | dated note after the paragraph |
| `docs/status/B.md` (rebuild-loss summary) | session-migration "built, not published"; hud "WIP" | dated note after the list |
| `docs/status/B.md` (appmenu paragraph) | "target2 has it (dpkg -i) and xsettingsd" | dated note: target2 is back on Clean-2 |
| `docs/research/indicator-units/README.md:41` | "in aptly" | dated note: binaries only, no source packages |
| `docs/research/rebuild-loss/README.md:33,35` | session-migration "not in aptly; nobody owns it"; overlay-scrollbar "deleted from resolute" | dated note after the table: A published session-migration; rmadison shows overlay-scrollbar in resolute and stonking; B-11 stub in aptly |
| `docs/research/unity-scopes/README.md:91-92` | files lens `locate` open | dated note: fixed by lens-files +unity1 (live check at the end of the file) |
| `docs/package-patches-b/README.md` | no rows for indicator-messages and calamares-settings-ubuntu | rows added, dated; calamares' export is in `research/calamares-oem/`, the 021/041 patches are on their unmerged task branches |

Not changed here: `docs/status/A.md:23` (A's target still listed with
libunity-gtk4-menu0 0.8) - that is agent A's status file; reported to the
coordinator.

Noted on the way: `scripts/append_record.py` always writes a blank line
before an entry, so bare table rows cannot continue the PATCHES table; the
corrections were appended as a titled section with its own table header.
