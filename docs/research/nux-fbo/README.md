# nux: FBO colour attachments index empty vectors (LP: #2160298)

Found by the stack-health sweep (`docs/STACK-HEALTH.md`, row nux). Reported on
Launchpad 2026-07-10 by riku55432, who got Unity crashing in
`libnux-graphics-4.0.so` when building with GCC 16, with a patch and a merge
request ([508190](https://code.launchpad.net/~riku55432/ubuntu/+source/nux/+git/nux/+merge/508190),
"Needs review" since 2026-07-10). Not fixed in the archive, in 26.10, or in
gitlab ubuntu-unity/unity/nux (no merge requests there; the file is unchanged
since the 2014 import).

## The bug

`IOpenGLFrameBufferObject::SetupFrameBufferObject()` sizes
`texture_attachment_array_` and `surface_attachment_array_` to
`GetMaxFboAttachment()` (8 here) and then calls `FormatFrameBufferObject()`,
which `clear()`s both. From then on `SetRenderTarget()`,
`SetTextureAttachment()`, `TextureAttachment()` and `Activate()` index the
empty vectors up to `GetMaxFboAttachment()`:

- it works by accident: `clear()` keeps the capacity, so the writes land in
  allocated memory, on elements whose destructors have already run;
- under `-D_GLIBCXX_ASSERTIONS` the first attachment aborts;
- the vector's destructor sees no elements, so whatever was attached last is
  never released.

## Proof

`fbo.cpp` creates a Nux window, an FBO and a 64x64 texture, attaches it,
activates, reads it back, drops the FBO and compares the texture's reference
count (`build-with-assertions.sh`, `run-against-tree.sh`,
`run-against-package.sh`, run in the `b-nux` chroot under `xvfb-run`):

| nux | Result |
|---|---|
| our tree, built with `-D_GLIBCXX_ASSERTIONS` | `SetTextureAttachment` aborts: `stl_vector.h:1263 ... Assertion '__n < this->size()' failed` (backtrace in `SetTextureAttachment`, from `fbo.cpp:31`) |
| same tree + fix | runs; attachment reads back; texture refs 1 -> 2 -> **1** after the FBO is gone |
| package 0ubuntu15+unity1 (shipped) | runs; texture refs 1 -> 2 -> **2**: the reference is leaked |
| package 0ubuntu15+unity2 | runs; refs back to **1** |

How often Unity itself leaks this way was not measured.

## Fix

`fix-fbo-attachment-arrays.patch`: reset the elements to null `ObjectPtr`s
instead of `clear()`ing the vectors, so they keep one slot per attachment.
Unlike the reporter's patch it needs no second query of the GPU for the size
(that query in `FormatFrameBufferObject()` could meet a null `GpuDevice`, which
`SetupFrameBufferObject()` guards against). Package
`4.0.8+18.10.20180623-0ubuntu15+unity2`, branch `b/fbo` of `packages/nux`
(commit `9793c23`, on top of `b/ubuntu15`), in aptly.

## Verification

- sbuild: all nux test suites pass (130, 9, 18, 113).
- Exported symbols of libnux-core, libnux-graphics and libnux identical to
  `+unity1`.
- target2 on `+unity2`: session starts, Dash searches with its blurred
  background (drawn through FBOs), HUD opens, no new crash reports.
- Agent A: Unity's `test-gnome-session-manager` 51/51 and
  `test-session-controller` 20/20 under plain xvfb-run against `+unity2`
  (test binaries from an earlier unity build, run against the new library).
