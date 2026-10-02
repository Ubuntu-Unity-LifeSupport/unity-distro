# UNITY-20260927-027: nux vidmode extra hunks and an in-tree FBO test

Owner: agent B (target2). This comes from the legacy reconciliation, B-L03.
nux `0ubuntu15+unity2` carries `fix-missing-vidmode.patch`. Besides the
proven fix (a server without XF86VidMode), that patch had two hunks "for a
double free", found by reading and never reproduced (PATCH_TOO_BROAD). The
FBO fix (`fix-fbo-attachment-arrays.patch`, LP #2160298) was proven only by
an out-of-tree program. The task:

- reproduce the double free, or prove it unreachable and remove the hunks
  (§4: not wider than proven);
- move the FBO check into nux's tests, fail before / pass after.

**Outcome.**

- **The double free is real, but only through the API.** The fullscreen
  branch frees the XF86VidMode mode list and the destructor frees it
  again. It is reproduced through the public API on Xorg (logs/01, 02), but
  neither Unity nor Nux itself ever asks for fullscreen. The hunk that
  clears the pointer now has its own patch and an in-tree test.
- **The other hunk is removed.** Freeing an old list before a new query
  guarded a leak (not a double free) on a second `CreateOpenGLWindow` on one
  display, which nothing does.
- **The FBO fix has an in-tree test.** Release: `0ubuntu15+unity3`.

```yaml
task_id: UNITY-20260927-027
package: nux
target_series: resolute
issue: legacy B-L03; LP #2160298 (FBO)
status: REPRODUCED
issue_search_result: NOT_FOUND  # the fullscreen double free; see "Search"; the FBO bug is LP #2160298 (found earlier)
source_version: 4.0.8+18.10.20180623-0ubuntu15+unity2 (9793c23, aptly) -> +unity3
source_commit: 0274bc5 (packages/nux, local branch b/UNITY-20260927-027: 336ec68, 5230f4c, ad4da6a, 85c6c4a, 35ecca4 for this task, then d50b77c, d869093, 0274bc5 from UNITY-20260928-020; exports in patches/)
observed: >
  FACT (logs/01, 02; target2, Xorg with XFree86-VidModeExtension, archive
  libnux 0ubuntu12, whose GraphicsDisplayX11.cpp is the same as ours apart
  from our patches): GLWindowManager::CreateGLWindow(..., fullscreen_flag
  true) at the current mode's size takes the fullscreen branch, which
  XFree()s the mode list. `delete` on the display XFree()s the same pointer
  again. The program exits 0 without checking. Under libc_malloc_debug with
  glibc.malloc.check=3 it aborts in ~GraphicsDisplay -> XFree with
  "free(): invalid pointer" (3 of 3).
  FACT (code, all shipped callers): Nux's WindowThread passes fullscreen
  false (WindowThread.cpp:1022); nux's gputests pass false; unity, the only
  reverse dependency of libnux in the archive, never calls CreateGLWindow or
  CreateOpenGLWindow. A second CreateOpenGLWindow on one GraphicsDisplay has
  no caller either (GLWindowManager creates a new display each time).
expected: a fullscreen display frees its mode list once; the FBO keeps its attachment slots and releases what it held
reproduction: fullscreen-direct.cpp + fullscreen-trace.bt (this directory); tests in the package (gtest-nuxgraphics)
evidence: logs/01-08, build-85c6c4a/
root_cause: >
  GraphicsDisplayX11.cpp fullscreen branch: XFree(m_X11VideoModes) with no
  reset, and ~GraphicsDisplay XFree(m_X11VideoModes).
root_cause_mechanism: dangling member pointer freed a second time in the destructor
invariant: >
  m_X11VideoModes is either owned (freed once, by the destructor) or NULL.
  The FBO attachment vectors keep GetMaxFboAttachment() slots, and the FBO
  releases what it holds.
existing_fix_result: NOT_FIXED  # see "Search"
candidate_approaches:
  - (A) keep both extra hunks as they were - rejected: the pre-query free is unproven and guards a leak on a path with no caller
  - (B) remove both - rejected: the fullscreen double free is reproduced in the public API, and the fix is one line with a test
  - (C) keep the pointer reset as its own patch with a test, drop the pre-query free - chosen
chosen_approach: C
why_chosen: the one hunk is proven (logs/02) and testable under the build's dummy Xorg; the other is not a double free and has no caller
alternatives_rejected:
  - the pre-query free: without it a second CreateOpenGLWindow on one display leaks the first list, a leak on a path nothing takes
design_challenger_required: false  # a one-line reset of a member pointer, and tests
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: GraphicsDisplay owns m_X11VideoModes; the branch that frees it early must clear it
defensive_workaround_rejected: not a guard; it restores the ownership rule the destructor relies on
code_risks:
  ownership_lifetime: checked  # the fullscreen branch does not read the list after the free; DestroyOpenGLWindow uses the copy m_X11OriginalVideoMode
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # no header change; see Result for the symbol comparison
unknowns:
  - the double free is reachable only by a caller outside the archive asking for fullscreen; no such caller is known
  - the gtest-nux-slow segfaults (logs/03, 07, 08) are explained and fixed in UNITY-20260928-020
```

## The two extra hunks of fix-missing-vidmode.patch

1. **After the fullscreen `XFree`, set the list to NULL** ("the destructor
   frees it again").
   - Reproduced (logs/01, 02). The earlier attempt could not reach the
     branch: it ran on the dummy driver at 1280x800, a size that server had
     no mode for. It also created the window twice.
   - `fullscreen-direct.cpp` creates one display in fullscreen at the
     current mode's size and deletes it. A uprobe trace shows the same list
     pointer passed to `XFree` twice.
   - Now its own patch, `fix-fullscreen-mode-list-double-free.patch`, with
     the test `TestGraphicsDisplayFullscreen.DestroyAfterModeSwitchFreesModeListOnce`
     in `gtest-nuxgraphics`. The test finds the current mode's size, and a
     gtest death-test child (threadsafe style, a fresh exec) creates and
     deletes the fullscreen display with AddressSanitizer preloaded. The
     test is skipped when the server has no XF86VidMode modes, and it fails
     if the child has no ASan. It does not check that the window was
     created: `GLWindowManager::CreateGLWindow` returns a display even when
     `CreateOpenGLWindow` fails early (no GLX, no visual), so such a child
     would exit 0 without reaching the branch. Control 2 shows the branch is
     reached in the build's dummy Xorg (Verifier finding 4). The test's
     stability also relies on UNITY-20260928-020's `-noreset`: the parent's
     own X connection could otherwise let the server reset before the child
     connects.
   - The first version detected the second free with glibc's malloc checking
     (`libc_malloc_debug`), as on target2. In the build it passed without the
     fix (control 1, logs/05): glibc missed the second free there. ASan's
     quarantine catches it (5 of 5 on target2; control 2, logs/06, reports
     the first free in `CreateOpenGLWindow` and the second in
     `~GraphicsDisplay`, GraphicsDisplayX11.cpp:180).
2. **Free an old list before querying a new one.**
   - The patch header said "both found by reading; the double free was not
     reproduced". This hunk is not a double-free fix at all. Without it, a
     second `CreateOpenGLWindow` on the same display overwrites the pointer:
     a leak of the first list.
   - No caller makes a second call (see `observed`). **Removed.**

`fix-missing-vidmode.patch` now contains only the missing-extension fix. Its
`else` branch still frees and clears a list that was returned with no modes.

## Search (2026-09-28)

- **Launchpad, nux (Ubuntu), "double free":** three 2011 compiz crashes
  (#869028 in `IOpenGLSurface::UnlockRect`, #862938, #872223), none in the
  XF86VidMode path.
- **Launchpad, "fullscreen":** nothing. Launchpad project `nux`: nothing.
- **gitlab ubuntu-unity/unity/nux:** GraphicsDisplayX11.cpp last changed in
  2015 (0a161815); no merge requests at all.
- **Ubuntu:** resolute 0ubuntu12, stonking 0ubuntu13, stonking-proposed
  0ubuntu15. 0ubuntu13-15 change pcre2, ICU and boost only; in the series
  only our two patches touch GraphicsDisplayX11.cpp.
- **Debian:** nux is not in Debian.

## FBO test

The check from `research/nux-fbo/fbo.cpp` is now
`tests/gtest-nuxgraphics-fbo.cpp` (`TestFrameBufferObject.ColourAttachmentIsKeptAndReleased`),
added by `fix-fbo-attachment-arrays.patch`. It attaches a 64x64 texture and
checks two things: that the attachment reads back, and that the texture's
reference count is back where it started once the FBO is gone. Without the
fix the reference leaks (research/nux-fbo: 1 -> 2 -> 2).

## Result

Fail before / pass after, in the package build (sbuild, resolute, dummy Xorg):

| build | TestGraphicsDisplayFullscreen | TestFrameBufferObject | log |
|---|---|---|---|
| control 2 (1d694a1): both tests, neither fix | **FAILED** (ASan double-free in XFree from ~GraphicsDisplay) | **FAILED** (refs 2, expected 1) | logs/06 |
| +unity3 35ecca4, three builds | OK | OK | logs/07 |
| control 1 (53d5639), malloc-check variant | passed (missed) | **FAILED** | logs/05 |
| +unity3 85c6c4a (malloc-check variant), second build | OK | OK | logs/04, build-85c6c4a/ |

- The exported symbols of libnux, libnux-core and libnux-graphics equal
  +unity2's (3420, 1052 and 1910; no differences).
- nux's suites 130 / 11 (was 9) / 18 pass in every build.

**The clean build came after UNITY-20260928-020.** The final source first
had no clean build: `gtest-nux-slow` (113 tests, the fourth suite; an
earlier version of this card called it `gtest-nux`) segfaulted in most
builds of 2026-09-28. That included the unchanged published +unity2 (0 of
2; logs/08), in `TestWindowThread.*` and `EmbeddedContext*`.

- **Not the chroot:** the build chroot's 446 package versions were
  identical to those of the passing build of 2026-09-24. An earlier
  version of this card guessed Mesa or GLib; that was wrong.
- **Two races in nux's own tests** (research/UNITY-20260928-020-nux-gtest-segfault):
  - the dummy X server reset between tests;
  - the `TestWindowThread` watchdog was deleted while it still ran.
- **Two test-only patches:** d50b77c `tests-dummy-xorg-noreset.patch` and
  d869093 `tests-windowthread-join-watchdog.patch`, with the changelog in
  0274bc5. They sit on top of 35ecca4 in the same `0ubuntu15+unity3`.

**sbuild of 0274bc5, three builds in a row: all successful**, suites
130 / 11 / 18 / 113 (`build/`: manifest and log of the third). Both new
tests of this task are OK in each. The exported symbols still equal
+unity2's.

## Not done

- target2 was used only for the API reproduction (logs/01, 02), then rolled
  back to `Clean-2` (checked inside: no `~/.dirty`, no libnux-4.0-dev, no
  test binaries).
- Independent verification: **PASS** (REVIEWED, 2026-09-28), together with
  UNITY-20260928-020, on the evidence and the clean build of 0274bc5. Its
  notes are in the card (death-test wording). `docs/PATCHES.md` and
  `docs/DECISIONS.md` entries were added through `append_record.py`.

## Gated build, ABI and target test (2026-09-29)

- **Gated build** of 0274bc5 (on GitHub `b/UNITY-20260927-027`) on the pinned chroot 20260929T201245Z: manifest PASS; suites 130 / 11 / 18 / 113 pass.
- **ABI** (logs/09): SONAME, NEEDED and the dynamic symbols of the three libraries (3420 / 1052 / 1910) are identical to the published +unity2. The patches change only .cpp and test files, and `/usr/include` is identical. So unity +unity12, built against +unity2 as `--extra-package` (UNITY-20260927-040), stays compatible.
- **Target test, mode this_build** (logs/10). target2 was full-upgraded from our repository, and the four gated .debs were installed on top, with sha256 equal to the manifest's.
  - After a reboot, compiz maps the new libnux with no deleted mappings, and the Unity panel and launcher are drawn.
  - `fullscreen-direct` under glibc malloc checking exits 0 in 3 of 3 runs, where the archive 0ubuntu12 failed 3 of 3 (logs/02).
- **Verifier round 2 on the gated build:** PASS (REVIEWED).

Remark: the key run shows the fix against the archive build, not against +unity2. +unity2's `fix-missing-vidmode.patch` already cleared the pointer, and +unity3 moves that line into its own patch. The FBO fix and the two test-only patches are covered by the build-time tests.

**This publication closes both tasks.** The one package, nux 4.0.8+18.10.20180623-0ubuntu15+unity3, carries UNITY-20260927-027 (vidmode double-free, FBO arrays) and UNITY-20260928-020 (the two test-only patches, card `research/UNITY-20260928-020-nux-gtest-segfault/`). The release gate and the publish record are those of -027. After -027 reaches PUBLISHED, -020 stays BLOCKED, with the reason "published as part of UNITY-20260927-027", until taskctl can close a task from another task's publish record (UNITY-20260929-023).

## Target verification of the publication (2026-09-29)

Result: **PASS** (logs/12). This used the normal upgrade path from Clean-2 (rolled back and checked inside) with our repository.

- The candidate for libnux-4.0-0 is +unity3 from 8080, and the full-upgrade installs nux +unity3 and unity +unity12.
- `dpkg -V` is clean.
- After a reboot, compiz maps the published libnux (sha256 equal to the gated build), and Unity draws its panel and launcher.

The key run (fullscreen-direct) is in logs/10, on the same bytes.
