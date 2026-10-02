# UNITY-20260927-002: unity +unity9's two third-party crash fixes, revalidated

Legacy A-L05. unity `+unity9` took the reporters' patches for LP #2160299 and
LP #2165662 (`research/unity-lp-crashes/`). The second has the shape of a
guard; this record checks whether it sits in the right layer. Agent A,
target `target-desktop`, 2026-09-28.

## Reproduction before and after (2026-09-28, same boot)

| Bug | unity +unity8 (before) | unity +unity11 (published, contains +unity9) |
|---|---|---|
| LP #2165662 - `tools/flicker-runs.sh 3` (shaped-flicker: an override-redirect window mapped/unmapped 200 times, shape alternating between a region and empty) | compiz crashed **3/3** (new PID, crash file, segfault in the journal) - `runs/flicker-unity8.txt` | 0/3, same compiz PID, no crash file - `runs/flicker-unity11.txt` |
| LP #2160299 - `tools/fm-default.sh set` (a file manager that is neither Nautilus nor Nemo as default for inode/directory, then restart compiz) | crash loop: `compiz ... segfault at 18 ... in libsigc-2.0.so.0`, unity7.service core-dumps until the default is restored - `runs/fm-default-unity8.txt` | compiz restarts, unity7 active, no crash file - `runs/fm-default-unity11.txt` |

## LP #2160299 - FileManager::GetDefault() (53d94899)

```yaml
root_cause: >-
  unity-shared/FileManager.cpp GetDefault() returned an empty Ptr when the
  default handler for inode/directory was neither Nautilus nor Nemo;
  TrashLauncherIcon connects to its signals when the launcher is built
  (research/unity-lp-crashes/runs/03-lp2160299-unity8-backtrace.txt).
invariant: GetDefault() never returns an empty pointer (every caller relies on it)
chosen_approach: fall back to Nemo, the same fallback the function already used when there is no default at all
correct_layer: >-
  GetDefault() is the function that promises a non-empty result; making it
  keep its promise for an unknown handler is the fix at the source, not a
  guard at a caller. The alternative - null checks in every caller
  (TrashLauncherIcon and the other users) - would spread the defect.
defensive_workaround_rejected: null checks at the callers (above)
outcome: confirmed in the right layer
```

## LP #2165662 - ComputeShapedShadowQuad() (1d618ed)

```yaml
root_cause: >-
  decorations/DecoratedWindow.cpp ComputeShapedShadowQuad() caches the shaped
  shadow pixmap keyed by the size in last_shadow_rect_. When the window's
  shape is empty it drops the pixmap (shaped_shadow_pixmap_.reset()) but
  keeps the key; when the shape comes back at the same size the size test
  says "cached", the build is skipped and the null pixmap is dereferenced
  (SimpleTexture::texture this=0x0,
  research/unity-lp-crashes/runs/01-lp2165662-unity8-backtrace.txt).
invariant: the shaped shadow is rebuilt whenever no valid pixmap for the current size exists
candidate_approaches:
  - "F1 (published): the cache test becomes 'no pixmap, or a different size',
    plus an early return 'if building failed'."
  - "F2: on an empty shape, clear last_shadow_rect_ together with the pixmap
    (as the no-SHADOW branch of ComputeShadowQuads() does)."
chosen_approach: keep F1's cache test as published
correct_layer: >-
  ComputeShapedShadowQuad() owns the shaped-shadow cache; a cache hit needs a
  stored value, so "no pixmap means rebuild" is the cache-miss test itself,
  in the function that owns the cache - not a guard at a caller. The size
  test only has meaning when a pixmap exists.
defensive_workaround_rejected: >-
  F2 alone does not cover every path that drops the pixmap: the generic
  branch of ComputeShadowQuads() (line 624) also resets
  shaped_shadow_pixmap_ while ComputeGenericShadowQuads() sets
  last_shadow_rect_ to a non-empty generic rect, so a window that turns
  rectangular and then shaped again at the same size would crash the same
  way (code read, Design Challenger, checked by the owner). Only F1's test
  covers all of them.
not_justified: >-
  F1's second part, `if (!shaped_shadow_pixmap_) return;` after the build,
  is dead code: BuildShapedShadowTexture() returns a CairoContext converted
  to its pixmap_texture_, created with std::make_shared and never null
  (unity-shared/CompizUtils.cpp:141-142, CompizUtils.h:113, checked by the
  owner). The 2026-09 record's "return if building failed" was wrong. It
  does no harm; remove it at the next unity upload made for another reason
  (no version for this alone).
measured: >-
  The owner's stale-shadow probe settles nothing: tools/shaped-stale.c +
  stale-probe.sh + stale-analyse.py show no shadow for this override-redirect
  window in phase 1 either (runs/stale-unity11.txt: only the window's own
  rectangle changes, while the same method does see an ordinary xterm's
  shadow, runs/stale-method-xterm.txt), so seeing nothing in phase 2 cannot
  show that the stale key is harmless.
unknowns:
  - "Possible wrong paint while the shape is empty (code read): with F1,
    last_shadow_rect_ stays non-empty, Draw() does not return early, quad 0
    keeps its old region and matrix, and ShadowTexture() falls back to
    SharedShadowTexture(); output extents stay stale too. Not observed - the
    probe window gets no shadow at all. F2 would make Draw() return early
    (without calling updateWindowOutputExtents(), which with a 0x0 rect would
    stretch the extents to the window's position, which is why the no-SHADOW
    branch does not call it). Needs a probe with a shaped window whose shadow
    is visible in phase 1 - proposed as a separate task."
  - "The cache key is the size only: a new shape with the same bounding box,
    or a colour change, reuses the old pixmap and quad region (code read)."
  - "LP #2160299: with an unsupported default file manager and Nemo not
    installed, file-manager actions fail silently instead of crashing."
design_challenger_required: true
design_review_result: APPROVE   # review 2
```

## Design review

Temporary Design Challenger, separate read-only subagent.

1. **REVISE**: keep both published code changes; the card had to name the
   cache owner as the layer, reject F2 for the generic-branch path, mark the
   post-build return as dead code, stop presenting the stale-shadow probe as
   evidence, and list the unknowns.
2. **APPROVE**: all addressed; both published fixes stay.

## Outcome

`ALREADY_FIXED` / `FIXED_LOCAL`: both +unity9 fixes are in the right layer
and still hold in the published +unity11 (reproduced before/after above).
Follow-ups, none needing a version now:

- remove the dead `if (!shaped_shadow_pixmap_) return;` at the next unity
  upload made for another reason;
- separate task proposed: whether a stale shaped shadow is painted (and
  output extents stay stale) while a shape is empty, with a probe window
  whose shaped shadow is visible, and whether to add F2 without
  updateWindowOutputExtents();
- noted: the shaped cache is keyed by size only.

