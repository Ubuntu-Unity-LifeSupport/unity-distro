# UNITY-20260928-014 - independent verification

## Round 1 (2026-09-29, ephemeral Verifier subagent; package 5d6a8c5, card 63ea58d)

Verdict: **INCOMPLETE**, `REVIEWED`. No FIX_INVALID, FIX_PARTIAL,
TEST_INVALID, ROOT_CAUSE_UNPROVEN or PATCH_TOO_BROAD finding.

What the Verifier checked:

- Scope matches design A'' with nothing added (4 files, +127/-7). The `users`
  field and the per-user closures are unchanged, and `update_greeter_user()`
  still runs on every pass that is not skipped.
- No re-entry: the settings writes reach only `handle_changed_*`, which do not
  migrate. Repeated passes are no-ops when the content is unchanged.
- The disassembly (dbgsym) shows the fresh list freed with `g_slist_free`
  only (its elements are weak) and not used after the loop. The builder's
  Variant is ref-sunk, compared, and unreffed.
- The deb and sbuild-log sha256 match the manifest; tests 12/12. The file list
  and Depends are identical to +unity3. Version ordering: +unity4 > +unity3 >
  0ubuntu1 and < stonking 0ubuntu4 (the normal case). The changelog is UTC.

Missing proof: in logs/20 the recovered values equal the stored ones, so the
skip path and the retry path are not visible. The request was a run where the
recovered value differs, optionally with a uprobe on
`greeter_sources_known`. The V3 kill is unconfirmed as being inside the
window (V3 still proves the fresh listing).

Remarks: dconf's same-value change signal was not checked; with lightdm-gtk
and `DISPLAY`, +unity4 no longer calls `update_login_layout` on unchanged
passes. The (0, 0) case (every listed user not yet loaded) writes the LightDM
layout alone; it was not seen.

Supplied after round 1: logs/21 (seeded `[fr]`, one write back to `[gb, us]`,
3 of 3) and logs/22 (uprobe trace, 3 of 3: skip `(0,1) -> 0` in the window;
recovery by LightDM `user-changed` with `(1,0) -> 1`; the manager retry
entered after the pending flag was cleared, so no second migration).
