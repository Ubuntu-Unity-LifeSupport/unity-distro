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
