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

## Design review (Design Challenger, 2026-10-13): APPROVE

No blocking findings. Taken into the code:
- the handle lookup can only return the real function, measured with stand-in libraries in every order; the
  self-check stays;
- the handle is kept, not closed (libgmodule is `NODELETE`; libgtk-4 is kept open by `try_hook()` the same way);
- when both lookups fail, `real` stays NULL so a later call retries (libgtk-4 can be loaded later), and the failure
  is logged once;
- the `gtk_widget_action_set_enabled` fallback is needed, and a test must reach it (below).

The reach is wider than PyGObject. Any process where libgmodule or libgtk-4 sits in a local `dlopen` scope while
ours is preloaded loses the lookup:
- Perl and Lua GObject bindings, and Gir.Core;
- a host that opens a GTK4 plugin `RTLD_LOCAL`.

In those processes GLib's own `g_module_symbol` calls failed too:
- GIO modules, so dconf fell back to memory;
- gdk-pixbuf loaders;
- GTK's input-method and print modules.

Not affected:
- gjs and Rust/gtk-rs, which link the libraries;
- `dlmopen` namespaces, where the preload is not present;
- setuid programs, where a preload by path is skipped.

With gtk-nocsd first in the preload, our `g_module_symbol` is never reached, as in 0.10. That order is not
changed by this fix.

Not taken: atomics for the two static pointer caches. The stores are idempotent, the same as in 0.10.

## The fix (0.11, `00fabde`)

`next_symbol()` takes the owner's soname. When `RTLD_NEXT` finds nothing:
- `dlopen(owner, RTLD_LAZY | RTLD_NOLOAD)`, then glibc's `dlsym` on that handle;
- the handle stays open;
- the debug log says `<name> is not in the global scope; taking <owner>'s own`.

The two callers pass `libgmodule-2.0.so.0` and `libgtk-4.so.1`, and log once if nothing is found. The README
describes the lookup. The library still links only libc (`NEEDED libc.so.6`, mode 0644). Build: `build/`,
sbuild resolute, PASS.

This also closes UNITY-20261013-015. A GTK4 plugin that a host without GTK opens `RTLD_LOCAL` lost every class
action disable under 0.10, because our `gtk_widget_action_set_enabled` did not find the real setter. In
`logs/08-localplugin.txt`, disable, activate, enable, activate gives:

| LD_PRELOAD | activations (right: 1) | lookup in the debug log |
|---|---|---|
| none | 1 | - |
| 0.10 | **2** (the disable was lost) | - |
| 0.11 | 1 | libgmodule's own, libgtk-4's own |

## Target tests (target2, 0.11 deb, cold boots with autologin)

| test | log | result |
|---|---|---|
| opt-out session, 0.10 (control) | 04 | 25 `AssertionError` lines; meld, gnome-tweaks, apps.py 3/4, unity-indicator-appearance, onboard exit 1; the Gio check fails at import |
| opt-out session, 0.11 | 05 | **0** `AssertionError` lines; unity-indicator-appearance and onboard run from autostart; meld, gnome-tweaks, apps.py 3/4, update-manager, software-properties-gtk, apport-gtk show windows, with menubars where the program has one; orca runs; `Gio.SettingsBackend` is `DConfSettingsBackend` and a write reads back from dconf; `cat` and a Python without gi map neither libgmodule nor libgtk-4 |
| every order, Xvfb | 06 | Python GLib import, apps.py 3/4, meld, gnome-tweaks, unity-indicator-appearance alive in all six orders (none; ours alone; before and after Ubuntu's gtk-nocsd; before and after gtk-nocsd built by its own `make`, the issue #1 build); alone, the log shows libgmodule's own; the RTLD_LOCAL plugin gives 1 activation in every order |
| the 0.9 card's `order-0.9.sh`, unchanged | 06 | identical to `docs/research/nocsd-order/order-0.9.txt` in all 50 rows (order, rc, menu lines): C and gjs programs as in 0.9 |
| both libraries, the session's default | 07 | the same programs as in 05, 0 `AssertionError` lines, the dconf check; the card's `classlive.sh` unchanged: the stand-in for `win.class-hello` follows `gtk_widget_action_set_enabled` both ways, activating it while disabled does nothing, while enabled prints `ACTIVATED win.class-hello` once |

gnome-tweaks prints one Traceback in every run, with and without any preload. It is a `GDBus.Error` for
`org.gnome.Shell.Extensions`, an interface that does not exist outside GNOME Shell. In the opt-out session the
second instance of onboard and of uwidgets-runner exits 0 at once, as in the session with both libraries.

On target2, besides the live archive and the test tools, these were installed for the tests:
- meld and gnome-tweaks;
- libadwaita-1-dev, to build gtk-nocsd;
- the GTK4 programs of `order-0.9.sh` as debs (gjs, gnome-text-editor, gnome-characters, gnome-calculator,
  nautilus, gnome-clocks, gnome-contacts, gnome-font-viewer, gnome-weather). None of them was on target2 before,
  so the first run of `order-0.9.sh` in logs/06 had rc 127; the log holds the rerun after the install.
