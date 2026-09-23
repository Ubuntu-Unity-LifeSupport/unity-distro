# Patch registry

Every patch we carry or intend to send gets a row here.

Status moves `draft` -> `ready` -> `sent` -> `merged` / `rejected`. A row is
`ready` only when its directory under `docs/upstream/` is complete and the
checklist in `CONTRIBUTING-UPSTREAM.md` section 9 passes. `sent` is set by
whoever sends it, which is always May.

| Package | Patch / change | What it does | Upstream | Where | Status |
|---|---|---|---|---|---|
| nux | `migrate-to-libpcre2.patch` (0ubuntu13) | Not ours. Adds the `nux.pc.in` and `configure.ac` hunks the 0ubuntu12 upload left out, so `nux-4.0` resolves again and unity can build. Asking for an SRU into resolute. | LP: #2103918, LP: #2147013 | [`upstream/nux-pcre2/`](upstream/nux-pcre2/) | **ready** |
| light-locker | `0003-Follow-the-user-s-display-session-outside-a-session-.patch`, `0004-Find-the-LightDM-session-when-XDG_SESSION_PATH-is-mi.patch` | Stops the abort on every login under Ubuntu Unity 26.04. light-locker runs under cinnamon-session, a systemd user service, so logind cannot map its PID to a session and `XDG_SESSION_PATH` is not inherited. Falls back to logind's display session and to LightDM's session list over D-Bus. Ours; 1.8.0-3ubuntu4+unity2. | LP: #2038808 | [`upstream/light-locker-session/`](upstream/light-locker-session/) | **ready** |
| unity | `GnomeSessionManager: only the session manager confirms a pending action` (commit on `unity/resolute`; native package, no quilt) | Unity waits for the session manager to call `EndSessionDialog.Open` back; cinnamon-session never does. After its dialog is cancelled the stale action either kills the session menu (known issue #2) or, if it was a restart, makes the next menu click restart the machine with no dialog. Only the owner of `org.gnome.SessionManager` may now confirm. Ours; 7.7.1+26.04.20260306-0ubuntu3+unity2 (`+unity1` fixed #2 only). Two unit tests. | none yet (MR to gitlab ubuntu-unity/unity, `ubuntu/devel`) | [`upstream/unity-stale-pending-action/`](upstream/unity-stale-pending-action/) | **ready** |
| unity | `GnomeSessionManager: show inhibitors before confirming a pending action`, `SessionController: bring a fading view back when asked to show again` (branch `wip/confirm-inhibitors`) | A restart or shutdown from the session menu went past applications that inhibit it: Unity confirmed its own pending action even when the session manager's `Open` listed inhibitors, and a new dialog requested while the old one faded out was ignored. Ours; 7.7.1+26.04.20260306-0ubuntu3+unity4 (`+unity3` had the first fix only, never published). | none yet | `research/shutdown-path/` | draft |
| cinnamon-session | `Ask-the-shell-for-the-end-session-dialog-when-Cinnamon-is.patch`, `Don-t-ask-a-Cinnamon-that-is-not-running-to-close-its-dia.patch` | Option A for known issue #6: when Cinnamon is absent, ask `org.gnome.Shell` for the end-session dialog after the query phase, as gnome-session does; stop two CRITICALs per cancelled end session. Ours; 6.4.2-1+unity1. **Blocked by the compiz exit race** it exposes. | none yet (feature request to linuxmint/cinnamon-session) | `research/shutdown-path/` | draft |
| compiz | XSMP die callback calls `exit(0)` with threads running | Crashes in the GDBus worker at logout when the bus is busy; frequent under #6 option A. Experiment: `_exit(0)`. | none yet | `research/shutdown-path/` | draft |
| unity | unit tests do not build on 26.04 | `-std=c++14` against googletest 1.17 (needs C++17); `tests/gmockvolume.c` fails under GCC 15 (`incompatible-pointer-types`). Harness workarounds only so far. | none yet | DECISIONS 2026-09-23 | draft |
| nux | `CreateOpenGLWindow` dereferences an unchecked XF86VidMode mode list | `GraphicsDisplayX11.cpp:297`: without the VidMode extension (Xvfb) any Nux window segfaults; this is what keeps Unity's tests from running under Xvfb. | none yet | DECISIONS 2026-09-23 | draft |
| nux | `Validator::Validate` discards its match result | On the Windows branch the function returns `Acceptable` from both sides of its `if`. Real, small, and deliberately kept out of the PCRE2 submission so it does not blur a first contact. | none yet | — | draft |

## Rules

- Patches live as quilt series in `debian/patches/`, managed with `gbp pq`.
  Exception: a `3.0 (native)` package such as `unity` has no patch series -
  changes are commits on `unity/resolute`, and the upstream copy is a
  separate branch cut from upstream's branch (see DECISIONS 2026-09-23).
- A patched Ubuntu package gets a `+unity1` version suffix. A package we build
  unmodified from upstream git keeps the upstream version, as `nux` 0ubuntu13
  does - we are not the author and should not claim to be.
- When Ubuntu ships a new version of a patched package, rebase the series onto
  it rather than carrying a fork.
- Anything that could plausibly land upstream goes upstream first. A `local`
  row sitting for a long time is a smell.
- Findings made in passing become their own row, never a passenger on someone
  else's patch.
