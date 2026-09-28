# UNITY-20260927-006: the scope of xorg-server 1.3+unity2

Revalidation of legacy item A-L21: `2:21.1.22-1ubuntu1.3+unity2` carries 31
upstream commits where the goal was 11 CVEs, and its changelog says "29".
Agent A, 2026-09-28. No code change in this task.

## Evidence card

```yaml
task_id: UNITY-20260927-006
package: xorg-server
target_series: resolute
issue: scope of the carried upstream series in 2:21.1.22-1ubuntu1.3+unity2 (legacy A-L21)
status: REPRODUCED   # the facts to check: 31 commits carried, changelog says 29
issue_search_result: FOUND
source_version: 2:21.1.22-1ubuntu1.3+unity2 (published in our aptly)
binary_version: 2:21.1.22-1ubuntu1.3+unity2 on target
source_commit: >-
  reconstructed repository Ubuntu-Unity-LifeSupport/xorg-server
  2ac6784be522445ffa0fd3dc3e3f6658e00809b7 (UNITY-20260928-003); patches in
  debian/patches/upstream-21.1.24/ and upstream-21.1-branch/
observed: >-
  31 upstream commits carried (carried-commits.txt, from the patch headers of
  our source), plus 8d604fa14 (FindGlyphRef); the +unity1/+unity2 changelog
  says "Carry the 29 fixes between upstream 21.1.22 and 21.1.24".
expected: >-
  every carried commit accounted for: which CVE it fixes, or why it is carried
existing_fix_result: FIXED_LOCAL
existing_fix_evidence: >-
  all 11 CVEs are fixed by commits we carry (table below); no resolute upload
  (1ubuntu1.1, 1.2, 1.3) fixes any of them - Launchpad changelog, and the
  Ubuntu CVE tracker shows resolute xorg-server "Needs evaluation" for all
  11; stonking has merged 21.1.24 (LP #2158792); Debian unstable has 21.1.24.
  Investigator sweep 2026-09-28T11:55Z (X.Org advisories 2026-06-02/04 and
  2026-07-08, 21.1.24 announcement, upstream git 21.1.22..21.1.24,
  Ubuntu and Debian trackers).
chosen_approach: >-
  keep 1.3+unity2 as published; correct the changelog wording ("29" -> 31,
  and the CVE-to-commit list) in the next upload of the package, which
  xorg-watch will trigger (a new resolute xorg-server above our base)
why_chosen: >-
  The 31 commits are exactly upstream's stable-branch point releases 21.1.23
  and 21.1.24 without the two version bumps and the two XQuartz/GL commits.
  Carrying that range is carrying what upstream released and what Debian
  unstable and Ubuntu 26.10 ship; a 12-commit CVE-only subset would be a
  combination nobody else builds or tests. The rest are small and local
  (below), none reported as a regression.
alternatives_rejected:
  - "CVE-only subset (12 commits: the 11 fixes plus d6fff22 which must travel
    with d6d9608): leaves out 11 upstream fixes for out-of-bounds / NULL /
    overflow bugs that upstream shipped in the same point releases, for no
    measured benefit (INFERENCE: no regression reported for any of them)."
  - "A new upload now only to fix the changelog text: changes the published
    version for wording; the correction rides on the next real upload."
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: not_applicable - no change
unknowns:
  - "8d604fa14 (FindGlyphRef) has no CVE in its message or the trackers; its
    upstream issues #1881/#1914 were not readable without a browser."
  - "Behaviour changes are read from the diffs (below), not measured; the
    runtime check of +unity2 was a smoke test and logout/login cycles
    (research/xorg-versioning)."
design_challenger_required: false   # no change
architectural_task: false
design_review_result: NOT_REQUIRED
```

## The 31 carried commits

Source: `carried-commits.txt` (full hashes and subjects of our patches);
CVE mapping from the X.Org advisories
(https://lists.x.org/archives/xorg-announce/2026-June/003705.html,
https://lists.x.org/archives/xorg-announce/2026-July/003716.html) and the
Debian security tracker "Fixed by" lines.

| Group | Commits (21.1-branch) | CVE / reason |
|---|---|---|
| CVE fixes (11 commits, 11 CVEs) | a569eb4f36ed | CVE-2026-50256 (ZDI-CAN-30136, font alias stack overflow; raises XLFDMAXFONTNAMELEN) |
| | f304b57444be | CVE-2026-50257 and CVE-2026-50260 (ZDI-CAN-30159/30163, XSYNC use-after-free) |
| | eced7e74cad4 | CVE-2026-50258 (ZDI-CAN-30160, XKB key types) |
| | 54c3d9fad0f2 | CVE-2026-50259 (ZDI-CAN-30161, XKB mapWidths) |
| | 92a167ab3fda | CVE-2026-50261 (ZDI-CAN-30164, XSYNC SyncChangeCounter) |
| | 94341bd715d6 | CVE-2026-50262 (ZDI-CAN-30165, GLX ChangeDrawableAttributes) |
| | 182c23f78040 | CVE-2026-50263 (ZDI-CAN-30168, CreateSaverWindow) |
| | f0b8e6e1d969 + 4926348d826b | CVE-2026-50264 (DRI2 GetBuffers; the messages name no id, the advisory and Debian do) |
| | f3df3c9a52b4 | CVE-2026-55999 (ZDI-CAN-30498, glamor font atlas) |
| | d6d96084f305 | CVE-2026-56000 (ZDI-CAN-30561, GLX context tags) |
| Must travel with a CVE fix | d6fff22bc8b4 | "GLX: Free the tag of the old context later" - named by the advisory as what makes 21.1.x vulnerable to CVE-2026-56000; carried only together with d6d96084f305 |
| Companion (INFERENCE) | 0f1f4bcbfb1f | negative glyph dimensions from a crafted PCF font (out-of-bounds write per its message); shipped next to the CVE-2026-55999 fix elsewhere; no advisory |
| Security-looking fixes without an advisory | c251243f282a, cc2bd590f368, 39befa04f92a, 7ee87732a90c, 5f2ac0de4798, 852bf24683d8 (XKB bounds / off-by-one / NULL), 1888711ce489 (GLX negative size), 8a6e5f0fcdf1 (colormap out-of-bounds read), ab2766f3473e (XIChangeCursorAttributes window check), c9cd39f9b7fc (Xi passive ungrab type checks), a29a7c1ec5b4 (xkb realloc failure) | 11 commits; no CVE, not called hardening by any tracker |
| Cleanup | 3e83c1085930 (meson option types), 2be25deaa6a7 (present: return created notifies), c285ed7dc6e4 (glx duplicate NULL assignment), f2f7b8293c1f (glamor error-path cleanup), 6c6a2dfd295f, bf25faf5c1b8, c0839d9cbf85 (dix warnings) | 7 commits |

11 + 1 + 1 + 11 + 7 = 31. Not carried from 21.1.22..21.1.24: the two version
bumps and the XQuartz/GL commits (834b40674448, b0be3a9e5a6f). Separately
carried: 8d604fa14969 (FindGlyphRef / FreeGlyph use-after-free, cherry-pick
of 67e7343b588a from the 21.1 branch after 21.1.24; closes xserver issue
#1881; no CVE found).

**Behaviour changes, read from the diffs:** a569eb4 raises the maximum XLFD
font name length (to match libXfont2); 2be25de makes `present` return the
notifies it creates (a bug fix); the DRI2 pair deduplicates attachments and
tracks the fake front buffer as booleans; the rest reject malformed requests
or input, or are build/warning changes. No commit changes a protocol or a
default.

## Outcome

`ALREADY_FIXED` / `FIXED_LOCAL`: 1.3+unity2 fixes all 11 CVEs; everything it
carries beyond them is upstream's own stable point releases, accounted for
above. To do at the next upload (triggered by xorg-watch when Ubuntu uploads
a resolute xorg-server above our base; none today - resolute-proposed still
has 1ubuntu1.3): changelog "29" -> "31", with the CVE -> commit list from the
table.
