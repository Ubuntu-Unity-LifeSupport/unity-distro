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

## Round 2 (2026-09-29, same Verifier; package 5d6a8c5, card aac89b3)

Verdict: **PASS** (PATCH_CORRECT), `REVIEWED`.

- The seeded proof shows the effect: 6 of 6 restarts (logs/21, logs/22) wrote
  exactly one value, `[gb, us]`, with no `[]` and no 4294967295. On +unity3 the
  same scenario writes both, so the pair is a real regression demonstration.
- The trace shows the skip itself, 3 of 3: `greeter_sources_known(0,1) -> 0`
  in the window, then LightDM user-changed with `(1,0) -> 1` and the write.
- Probe identity was checked in the binary and dbgsym. lambda27 (manager
  user_changed) tests the pending flag and jumps to migrate_input_sources
  (0x102f0); lambda29 jumps there unconditionally. So "lambda27 entered, no
  migration" shows the flag was cleared by the complete pass.
- A retry migration was never observed. That is accepted as a stated
  limitation: the gate is a fallback nothing observed needs, and the
  logs/06 stuck state came from the stale snapshot that the fresh list fixes
  (V3).

Remarks: keep the unobserved retry migration and the unobserved partial
multi-user union listed as limitations. The logs/21-22 timings are counted
from the restart action, so they differ from the 0.25 s skip-to-write gap.
Not checked: dconf same-value notification (it matters only with DISPLAY for
update_login_layout); the (0,0) not-yet-loaded case, which is recorded in the
card.

## Round 3 (2026-09-29, ephemeral Verifier subagent; gated build of 5d6a8c5 on chroot 20260929T201245Z)

Verdict: **PASS**. Review status: `INDEPENDENTLY_REPRODUCED`. Question: does the gated build ship exactly the reviewed and target-tested change?

- **Manifest.** PASS, and all 6 artifacts, the log, the chroot tarball, its sidecar and sbuild-config.pl match. The source tree 07661b25 equals 5d6a8c5^{tree}. The commit is on our GitHub as `b/UNITY-20260928-014`.
- **sbuild.** `Status: successful`; the unit tests ran (TAP 1..12, all ok).
- **Source.** The unpacked .dsc equals `git archive 5d6a8c5`, and `git diff 10eb95c 5d6a8c5` is the reviewed change (logs/17).
- **Against the tested build.** `dpkg-deb -R` of the gated .deb and dbgsym is identical to ~/work/b/ik4/out2, DEBIAN/control included. That is the build installed and tested on target2 (logs/20). Only the container sha256 differs (logs/23).
- **Build dependencies.** 130 Installed-Build-Depends changed; they are SRU/security point updates. They cannot change behaviour, because every shipped file and the shlibs-derived Depends are byte-identical.
- **Changelog.** The trailer is UTC, and the version order is +unity4 > +unity3 > 0ubuntu1.

Remark: the gated-vs-tested log was renumbered to 23, because 21 and 22 were already used.
