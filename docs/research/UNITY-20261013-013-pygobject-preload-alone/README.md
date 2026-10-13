# UNITY-20261013-013: PyGObject fails at import when libunity-gtk4-menu is preloaded without gtk-nocsd

Found during UNITY-20261012-004: test programs written in Python failed when only `libunity-gtk4-menu.so.0` was
preloaded.

**The failure.**
- With `LD_PRELOAD=/usr/$LIB/libunity-gtk4-menu.so.0`, nothing else, the first `from gi.repository import GLib` of
  any PyGObject program stops with `AssertionError` in `gi/overrides/__init__.py:209` (`assert g_type != TYPE_NONE`).
- That configuration is exactly what a Unity session has after the user's documented gtk-nocsd opt-out (an empty
  `~/.config/environment.d/50-gtk-nocsd.conf`; UNITY-20261012-005, UNITY-20261013-001 s2).

## In a real session (target2, live archive, cold boot with autologin)

Both sessions ran with libunity-gtk4-menu0 0.10 and libgtk-nocsd0 4.8-1+unity4 from the live archive. Script:
`session-check.sh`. Programs were started through the user manager, as the launcher does.

| | s0 control (logs/02) | s1 opt-out file (logs/03) |
|---|---|---|
| user manager and compiz `LD_PRELOAD` | `/usr/$LIB/libunity-gtk4-menu.so.0:/usr/$LIB/libgtk-nocsd.so.0` | `/usr/$LIB/libunity-gtk4-menu.so.0` |
| unity-indicator-appearance (autostart, panel) | running | **exits 1, `AssertionError`** |
| onboard (autostart when the screen keyboard is on) | running | **Traceback at import** |
| meld (GTK3, Python) | window, menubar | **exits 1** ("Meld requires Gtk+ 3.20 or higher": its version check fails on the broken import) |
| gnome-tweaks (GTK4 + libadwaita, Python) | window, menubar | no window after 8 s, no error in its journal |
| `apps.py 3` (minimal GTK3 window) | window shown | **exits 1, `AssertionError`** |
| `apps.py 4` (minimal GTK4 window) | window shown | **exits 1, `AssertionError`** |
| `AssertionError` lines in the user journal | 0 | 10 |

The session itself comes up: compiz, the panel and the C programs are not affected. What breaks is every program
that imports `gi` from Python. Those include session components:
- unity-indicator-appearance;
- onboard and orca, the accessibility tools;
- uwidgets-runner;
- apport-gtk, the printer applet, update-manager and software-properties.

All of them are on the target image.

Why s0 is not the first control: the session target2 had at hand started before the upgrade. Its user manager held
only `libgtk-nocsd.so.0`. Both rows above come from fresh boots.

## Since when (logs/01)

The library files of every published deb were extracted from the archive and preloaded by path (not installed):

| version | exports `g_module_symbol` | alone | alone + libgmodule | before gtk-nocsd | after gtk-nocsd |
|---|---|---|---|---|---|
| 0.5 | no | ok | ok | ok | ok |
| 0.6 | yes | **AssertionError** | ok | ok | ok |
| 0.8 | yes | **AssertionError** | ok | ok | ok |
| 0.9 | yes | **AssertionError** | ok | ok | ok |
| 0.10 | yes | **AssertionError** | ok | ok | ok |

So this is not a regression of 0.9 (issue #1's fix). It came with 0.6, commit 0ce1eb1 "Reach gjs and PyGObject
applications", the version that started wrapping `g_module_symbol`.

## Cause

`g_module_symbol()` in our library looks up the real one as "the next definition after ours":
- in 0.6-0.8, `dlsym(RTLD_NEXT, "g_module_symbol")`;
- since 0.9, the same through glibc's own `dlsym` (`next_symbol()`).

`RTLD_NEXT` only searches objects in the global scope that come after ours, and in a Python process libgmodule is
not one of them:
- `python3` and `gi/_gi*.so` do not link libgmodule.
- Python opens extension modules with `RTLD_NOW` and without `RTLD_GLOBAL`; `sys.getdlopenflags()` is 2.
- libgmodule arrives as a dependency of libgirepository, inside `_gi`'s local scope.
- But `_gi`'s calls to `g_module_symbol` bind to ours, because a preloaded library is first in every lookup scope.

So the lookup returns NULL. Our `g_module_symbol` then answers FALSE for every name. GObject Introspection cannot
resolve `g_main_loop_get_type` and the other `*_get_type` functions, and the overrides see `TYPE_NONE` for
`GLib.MainLoop`.

Measured (logs/01):
- With `_gi` opened `RTLD_NOW | RTLD_GLOBAL` (`sys.setdlopenflags` before the import), 0.10 alone imports fine.
- With libgmodule preloaded next to us, so that it is in the global scope after us, 0.10 alone imports fine.

Why gtk-nocsd hides it: preloaded after us, it is the "next" definition, and it fetches the real `g_module_symbol`
from `dlopen("libgmodule-2.0.so.0")` by name, not through `RTLD_NEXT`. gjs is not affected: libgjs links
libgirepository, which links libgmodule, so libgmodule is in the global scope at start. C programs link GTK, which
links libgmodule, so they are not affected either.

Our second wrapped function, `gtk_widget_action_set_enabled`, uses the same lookup; libgtk-4 is opened by
GObject Introspection through `g_module_open`, which is global, so the measurement found no failure there. The fix
covers it the same way.

The cause is in `next_symbol()` and its callers only. It does not touch the UNITY-20261012-004 code (menus after
realize).

## Upstream gtk-nocsd (logs/01)

Our menu commits in GTK-NoCSD (3b1d4a3..2d50fe9) live inside gtk-nocsd itself, and gtk-nocsd resolves
`g_module_symbol` with `dlopen("libgmodule-2.0.so.0", RTLD_LAZY)` plus its saved `dlsym`
(`GTKNoCSDGetLibrary`, `LOAD_SYMBOL`), not with `RTLD_NEXT`. Measured with a build of fd4b76a, preloaded alone: GLib,
Gtk 3 and Gtk 4 import with `GTK_NOCSD_MENU=0` and `=1`. Upstream does not have this defect.

## Why it was missed

None of the tests that ran our library without gtk-nocsd started a Python program:
- the 0.9 order runs (`docs/research/nocsd-order`, `order-0.9.sh`) put the library alone in front of C and gjs
  programs only; gnome-music and gnome-tweaks were checked only in the live session, where gtk-nocsd was
  preloaded too;
- the opt-out step of UNITY-20261012-005/-006 (`gate/target-test.txt` step 6) and UNITY-20261013-001 s2 checked
  the environment, the maps and C programs (gnome-calculator, gnome-disks).

## Proposed fix (for the Design Challenger; no code in the branch yet)

In `next_symbol()`, when `RTLD_NEXT` finds nothing, take the definition from the library that owns the function:
- `dlopen(<soname>, RTLD_LAZY | RTLD_NOLOAD)`, which only succeeds if that library is already loaded;
- then glibc's `dlsym` on that handle, with the self-check kept;
- sonames: `libgmodule-2.0.so.0` for `g_module_symbol` and `libgtk-4.so.1` for `gtk_widget_action_set_enabled`.

`RTLD_NEXT` stays first, so with gtk-nocsd after us the chain through gtk-nocsd is unchanged. With `RTLD_NOLOAD` we
never load a library into a process that does not have it, and the library still links only libc. A prototype
(scratchpad, not committed) made all three orders import on target2. Its debug line shows the path taken:
`g_module_symbol is not in the global scope; libgmodule-2.0.so.0's own: 0x…`.

Open point for the review: keep the handle (it pins the library while we hold its function) or `dlclose` it after
the lookup.

Version: the fix is small and independent of UNITY-20261012-004, so per the coordinator it becomes 0.11 on top of
0.10. UNITY-20261012-004 moves to 0.12 and UNITY-20261013-008 to 0.13.
