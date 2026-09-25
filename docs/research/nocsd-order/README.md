# unity-gtk4-menu next to gtk-nocsd: preload order (issue #1)

Agent B, 2026-09-25, on `target2`. Prompted by issue #1 in unity-distro from
MorsMortium, gtk-nocsd's maintainer (not answered - May is not corresponding
yet). His first claim: with gtk-nocsd first in `LD_PRELOAD`, preloading both
libraries "caused a segfault at all times". Our README said the order did not
matter, based on a test with the 0.1-era shim (`DECISIONS.md`, 2026-09-23 entry
on gtk-nocsd coexistence) - before the shim hooked `g_module_symbol` (0.6) and
`gtk_widget_action_set_enabled` (0.7).

## What was run

Under Xvfb on `target2`, `XDG_CURRENT_DESKTOP=Unity`, 7 s per run, exit 124 =
still alive at timeout, 139 = SIGSEGV. Three gtk-nocsd builds:

- `libgtk-nocsd.so.0` - Ubuntu's build, 4.8-1+unity1 from our aptly (`-O2`,
  Ubuntu's `-Wl,-Bsymbolic-functions`);
- `nocsd-head/libgtk-nocsd.so.0` - codeberg head `6b1f70a`, plain `make`, as
  its maintainer builds it (no `-O`, no `-Bsymbolic-functions`), built in the
  `b-dev` chroot (libadwaita-1-dev added there);
- no gtk-nocsd.

Scripts: `order-0.8.sh` (0.8 installed), `order-0.9.sh` (0.9 installed).

## 0.8: he is right, and the fault is ours

With Ubuntu's gtk-nocsd build: no crash in either order, 6 applications -
which is why we never saw it. With gtk-nocsd head built by `make`:

| | nocsd head alone | shim, then nocsd head | nocsd head, then shim |
|---|---|---|---|
| gnome-text-editor | alive | **SIGSEGV** | **SIGSEGV** |
| gnome-characters | alive | **SIGSEGV** | **SIGSEGV** |
| gnome-calculator | alive | **SIGSEGV** | **SIGSEGV** |
| nautilus | alive | **SIGSEGV** | alive |
| gnome-clocks | alive | **SIGSEGV** | alive |

So it crashes in **our** order too, not only in his. gdb on gnome-calculator:
thousands of frames of `g_module_symbol () from libunity-gtk4-menu.so.0`
calling itself.

**Mechanism.** gtk-nocsd defines its own `dlsym()`; for about 40 names,
`g_module_symbol` among them, it ignores the handle and returns
`g_module_symbol` - the address of "its" function. Without
`-Bsymbolic-functions` that address is taken through its GOT, and the GOT
entry binds to the first definition in the process: ours. Our shim fetched
the real function with `dlsym(RTLD_NEXT, "g_module_symbol")`, which lands in
gtk-nocsd's `dlsym` (we define none), got itself back, and recursed. Ubuntu's
build adds `-Bsymbolic-functions`, binding the reference locally, so the
answer was gtk-nocsd's own wrapper and all was well. A second path on the
same theme (found by reading, consistent with the table): at `-O0` gtk-nocsd's
`dlsym` calls the real one with a normal call, so glibc counts `RTLD_NEXT`
from gtk-nocsd, not from us; with gtk-nocsd first, the "next"
`gtk_widget_action_set_enabled` after gtk-nocsd is our own.

## 0.9: the fix

Look the next definition up with glibc's own `dlsym`: `dlvsym(RTLD_DEFAULT,
"dlsym", "GLIBC_2.34")` returns glibc's (versioned; gtk-nocsd's is not), and
calling that from our code makes `RTLD_NEXT` count from us. A "next" that is
ourselves is never called.

A first attempt, `dlvsym(RTLD_NEXT, "g_module_symbol", <any version>)`, does
**not** work: every object that links glibc has a version table, and then
glibc refuses an unversioned symbol under any version asked. It fell back to
`dlsym`, still got itself, and gjs applications exited (`rc=1`) because the
lookup returned FALSE. Recorded so nobody tries it again.

Result with 0.9 as packaged (`order-0.9.txt`, 10 programs x 5 orders): no
crash in any run. (The `gjstest.js` lines there show rc=1 because the script
must be run with `gjs -m`; re-run that way in all 6 orders including no
preload: alive in all, menu hooked wherever the shim is first.)

What the orders do now:

- shim first - the session's order (`60-unity-gtk4-menu.conf` is applied
  after `50-gtk-nocsd.conf` and each prepends): global menu for C, gjs and
  Python applications, with either gtk-nocsd build.
- gtk-nocsd first: no crash, C applications get the menu, **gjs and Python
  ones do not** (gnome-characters, gnome-weather, gjstest): gtk-nocsd resolves
  the real `g_module_symbol` through libgmodule's handle, so a library after
  it never sees GObject Introspection's lookups. That is its design, not a
  bug; the shim cannot fix it from behind.

Not verified here: the panel itself in a live Unity session (the runs count
the shim's own debug lines for hooking and export). The export path did not
change in 0.9, only how two function pointers are found.

## His second claim, case by case

- **Gir.Core (.NET) loading GTK through raw `dlsym`**: not covered. Such a
  process does not link libgtk-4 and never calls `g_module_symbol`, so the
  shim never hooks - no menu, no harm. gtk-nocsd covers it through its
  `dlsym` override. No Gir.Core application is in the 26.04 archive; not
  run.
- **Ardour's GTK2 fork**: outside the shim's scope (GTK4 only); GTK2/3
  global menus go through `appmenu-gtk-module`.
- **Statically linked GTK4**: not covered - the shim finds no libgtk-4 and
  does nothing. gtk-nocsd falls back to `RTLD_DEFAULT`.

His third claim - one library instead of two - is answered in
`docs/DECISIONS.md` (2026-09-25, "unity-gtk4-menu stays separate for now").
