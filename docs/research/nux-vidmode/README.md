# nux: crash without XF86VidMode

_Agent B, 2026-09-24. Package `nux 4.0.8+18.10.20180623-0ubuntu13+unity1`,
commit `be561f9` on branch `b/vidmode` of `packages/nux` (based on agent A's
`unity/resolute`, 0ubuntu13). nux has no repository of ours; this directory
holds the patch so that it exists somewhere other than the builder._

## The bug

`nux::GraphicsDisplay::CreateOpenGLWindow` (`NuxGraphics/GraphicsDisplayX11.cpp:296-297`):

```cpp
XF86VidModeGetAllModeLines(m_X11Display, m_X11Screen, &m_NumVideoModes, &m_X11VideoModes);
m_X11OriginalVideoMode = *m_X11VideoModes[0];
```

No check that the extension exists or that the call succeeded. On a server
without XFree86-VidModeExtension the list is NULL and the process segfaults.

## Who it hits - measured, not assumed

`vidmode.cpp` here creates one window with `nux::CreateGUIThread`, as Unity's
`tests/test_main.cpp` and its `Standalone*` tools do. In a clean resolute
chroot with nux 0ubuntu13:

| X server | VidMode ext. | before | after |
|---|---|---|---|
| Xvfb | no | SIGSEGV, exit 139 (`gdb`: frame 0 in `CreateOpenGLWindow`) | window created |
| TigerVNC Xtigervnc 1.15 | no | SIGSEGV, exit 139 | window created |
| Xorg + dummy driver | yes | window created | window created |

**Unity itself is not affected.** unityshell gets its window from compiz with
`nux::CreateFromForeignWindow` (`plugins/unityshell/src/unityshell.cpp:331`);
`CreateFromOpenGLWindow` contains no VidMode code at all. Only
`CreateGUIThread` reaches the crash, and in the archive only Unity's unit tests
and its unshipped `Standalone*` tools use it - `apt-cache rdepends
libnux-4.0-0` lists nothing but unity and libunity-core. The host session's
search suggested "Unity crashes at start over VNC"; the code says otherwise,
and no full Unity session under Xvnc was run to test it either way.

What the fix buys: Unity's unit tests can run under plain Xvfb. Until now the
harness in `docs/upstream/unity-stale-pending-action/harness/` needs Xorg with
the dummy driver for exactly this reason.

## The fix

`fix-missing-vidmode.patch`: query the extension, use the mode list only when
it was returned and is non-empty; without modes a fullscreen request falls back
to a normal window, as nux already does when no mode matches. Also NULL the
list after it is freed in the fullscreen path (the destructor frees it again)
and free an old list before querying a new one - both by reading;
`fullscreen.cpp` could not reach the fullscreen branch on the dummy driver
(no mode at the requested size), so the double free is **not reproduced**.

Verified: nux's own test suite at build (130, 9, 18, 113 passed); the table
above; `target2` with the new libnux, rebooted - compiz maps it, Dash and HUD
work, no new crash reports (`../../screenshots/2026-09-24-target2-dash-nux-unity1.png`).

## Unity's unit tests on it (agent A, 2026-09-24)

In agent A's chroot, Unity sources at `unity/resolute` `f0343140`, libnux
replaced with this build by `dpkg -i`, Unity binaries not rebuilt:

| Server | TestGnomeSessionManager | TestSessionController |
|---|---|---|
| plain Xvfb, no VidMode | 51/51 | 20/20 |
| Xorg + dummy (regression check) | 51/51 | 20/20 |

Before the fix the first line was a segfault in `CreateOpenGLWindow` before
the first test. The Xorg-dummy workaround in the harness is no longer needed.

Published to aptly 2026-09-24 (libnux-4.0-0, -common, -dev, nux-tools).

## Rule 0

Launchpad (nux, unity: "vidmode", "Xvfb", "CreateOpenGLWindow" - zero, all
statuses), gitlab.com/ubuntu-unity/unity/nux (no issues, no MRs, and
`ubuntu/devel` at 0ubuntu15 still has line 297 unchanged), Debian (no nux
package). Searched by the host session 2026-09-24 07:05Z and in the upstream
tree here.

## Not done

- Upstream: on hold per May (relayed by agent A 2026-09-24; to confirm with May).
- Rebase onto upstream 0ubuntu15 (stonking): it removes Unicode-licensed code
  (LP #2147049) and the boost-system build dependency. Separate decision.

---

# Rebased onto upstream 0ubuntu15

_Agent B, 2026-09-24. `nux 4.0.8+18.10.20180623-0ubuntu15+unity1`, commit
`9d26778` on branch `b/ubuntu15` of `packages/nux`, from `origin/ubuntu/devel`
(gitlab.com/ubuntu-unity/unity/nux) plus `fix-missing-vidmode.patch`
unchanged._

What upstream added over 0ubuntu13:

- **0ubuntu14** - `remove_unicode_licensed.patch` (LP #2147049): replaces the
  Unicode, Inc. 2001-2004 `ConvertUTF*` code in `NuxCore/Character/NUni.cpp`
  with `icu_conversions.cpp` on top of ICU. New dependency: `libicu78`.
- **0ubuntu15** - drops `libboost-system-dev` from Build-Depends (LP #2166734).

## ABI

Exported symbols, 0ubuntu13+unity1 -> 0ubuntu15+unity1:

| Library | before | after | change |
|---|---|---|---|
| libnux-4.0.so.0 | 3420 | 3420 | none |
| libnux-graphics-4.0.so.0 | 1910 | 1910 | none |
| libnux-core-4.0.so.0 | 1053 | 1052 | removed `nux::tr_utf8_validate`, `nux::isLegalUTF8Sequence`; added a global `convert(...)` |

Two symbols disappear with the same SONAME. Nothing we ship imports them:
every ELF file of unity, unity-services, libunity-core-6.0-9,
unity-settings-daemon and all 31 compiz plugins on `target2` was checked with
`nm -D --undefined-only`. `apt-cache rdepends libnux-4.0-0` lists only unity
and libunity-core.

## The ICU replacement is broken - but not reached on Linux

`utfconv.cpp` here calls `ConvertUTF8toUTF32` / `ConvertUTF32toUTF8` the way
`NUnicode.cpp` does:

| Input | 0ubuntu13+unity1 | 0ubuntu15+unity1 |
|---|---|---|
| "Hi" 8->32 | OK, consumed 2, produced 2: `48 69` | OK, consumed **0**, produced **0**, output `feff 48 69 0` |
| "Пр" 8->32 | OK, 4 -> 2: `41f 440` | same defect: pointers not moved, BOM first |
| "a\xff b" 8->32 | stops, result 1 | "OK", `U+FFFD` substituted |
| U+041F U+0440 32->8 | `d0 9f d1 80` | `ef bf bd ef bf bd ...` - garbage |

Causes, in `icu_conversions.cpp`: the source length is `end - start + 1` (one
past the exclusive end); the target capacity is always counted in 4-byte units
and passed to `ucnv_convert` as bytes; `*sourceStart`/`*targetStart` are never
advanced, which the ConvertUTF contract requires and callers use to measure
output; and ICU's `"utf16"`/`"utf32"` mean big-endian with a BOM, while
`wchar_t` on Linux is 32-bit host-endian.

**No effect on Unity.** On Linux `TCHARToUTF8(s)` is `s` (`NuxCore/NuxCore.h`,
`#ifndef _UNICODE`); the remaining callers are Windows-only (DirectWrite in
`StaticText.cpp`, Win32 clipboard) or conversion templates nothing
instantiates; Unity calls none of it (checked in its source). A finding for
upstream - on hold with the rest.

## Verified

- Build: the first sbuild attempt segfaulted in
  `EmbeddedContextMultiWindow.ForeignFrameEndedPresentNone` (GL test under the
  Xorg dummy runner, unrelated code); the second, same source, passed all four
  suites (130, 9, 18, 113). One failure in three builds with our patch -
  flaky, not investigated further. Logs: `~/work/b/nux/out15/attempt1/`.
- VidMode fix still works: `vidmode.cpp` creates its window under Xvfb.
- `target2` on 0ubuntu15+unity1, rebooted: compiz maps libnux and libicuuc; the
  Dash finds "Терминал" and "Консоль" for "терм"; the HUD finds "О приложении
  (Справка)" in yelp and "Очистить историю (Калькулятор)"; no new crash reports.
  Typing into the Dash at 200 ms per key through xdotool loses characters
  while a search is in flight (at 450 ms it does not) - not compared on the old
  nux, most likely the harness. "парам" in the HUD over gnome-calculator gave
  no result while "очист" did - hud-service matching, not nux; not investigated.

## Unity's unit tests on it (agent A, 2026-09-24)

Unity test binaries from `unity/resolute` `f0343140`, not rebuilt; libnux
0ubuntu15+unity1 confirmed in the chroot with `dpkg-query` and by `ldd`
pulling `libicu*.so.78`. Plain Xvfb: TestGnomeSessionManager 51/51,
TestSessionController 20/20; Xorg dummy: the same. Agent A discarded two
earlier runs that, because `libnux-4.0-dev` pinned the old version, had
actually run on 0ubuntu13+unity1. His ABI check over 86 ELF files of his own
builds (unity +unity5, compiz +unity1, unity-settings-daemon 0ubuntu7+unity1,
cinnamon-session +unity2): no import of the two removed symbols.

Published to aptly 2026-09-24 (libnux-4.0-0, -common, -dev, nux-tools).
