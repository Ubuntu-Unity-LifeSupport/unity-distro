# unity-gtk4-menu built into gtk-nocsd (experiment)

Agent B, 2026-09-25, on `target2`. May asked what it would take to stop
carrying two preloaded libraries (issue #1's third point, DECISIONS
2026-09-25 "unity-gtk4-menu stays separate for now") and to try it. Not
released: nothing in aptly, nothing sent to gtk-nocsd's maintainer.

## What was done

Base: our gtk-nocsd `4.8-1+unity1` (`packages/gtk-nocsd` branch
`unity/resolute` at 92ed59e, Debian 4.8-1, no patches). The experiment lives
in agent B's clone, `~/work/b/nocsd-merge/pkg`, branch `b/global-menu`
(cafe5a2, not pushed anywhere - `packages/gtk-nocsd` is agent A's). Built as
`4.8-1+unity2~menu1` in sbuild.

`global-menu.patch` (quilt, one patch):

- `Source/GlobalMenu.c` - unity-gtk4-menu 0.9's source, second compilation
  unit of the same library. Diff against 0.9: +41 -89. Removed: its own
  `g_module_symbol()`, the `next_symbol()`/`dlsym@GLIBC_2.34` lookup of 0.9,
  the self aliases, the constructor. Added: `GTKNoCSDMenuInit()` and
  `GTKNoCSDMenuLookup(name)`, both hidden. The real
  `gtk_widget_action_set_enabled` now comes from libgtk-4's own handle
  through gtk-nocsd's `o_dlsym` (glibc's dlsym) - no `RTLD_NEXT` anywhere,
  so issue #1's failure has nothing left to act on.
- `Source/GTK-NoCSD.c` - 14 lines added, nothing changed: two declarations,
  `GTKNoCSDMenuInit()` at the end of its constructor, `GTKNoCSDMenuLookup()`
  in its `g_module_symbol()` (after it has fetched its own GTK/libadwaita
  types - the order the two libraries needed too) and in its `dlsym()`, and
  `gtk_widget_action_set_enabled` in its `GET_SYMBOLS` list so both lookups
  hand ours out.
- `Makefile` - compiles both files; adds `gio-unix-2.0` to the header path.
- The GSettings schema `com.ubuntu-unity.gtk4-menu`, installed by the package.

Packaging (`packaging.diff`): `Breaks`/`Replaces: libunity-gtk4-menu0` (its
schema moves, and both preloaded at once would hook twice), one symbol added
to `libgtk-nocsd0.symbols` (`gtk_widget_action_set_enabled`), the schema in
`libgtk-nocsd0.install`.

The library still links libc only (`readelf -d`: one NEEDED), and exports
nothing new except `gtk_widget_action_set_enabled`. Licences are
compatible: gtk-nocsd is GPL-3+, the shim LGPL-3.0-or-later.

## Measured

On `target2`: `libunity-gtk4-menu0` removed, the merged `libgtk-nocsd0`
installed, rebooted. The session's `LD_PRELOAD` is `libgtk-nocsd.so.0` alone.

- **Session**: panel, unity-settings-daemon, nemo-desktop and the indicators
  up; no crash report; the boot's error log has the same sources as the two
  boots before it (kernel vmwgfx, pulseaudio, xdg-desktop-portal, light-locker
  #5) and nothing from either library.
- **18 GTK4 applications** (the `breadth` set of `research/layer-b/`, run
  from the session's own environment): menu exported for 18/18, and the
  per-item audit is the same as with the two libraries
  (`breadth-two-libraries.txt` vs `breadth-merged-installed.txt`). The one
  difference, gnome-system-monitor without a menu in the two-library run, was
  a one-off: 3 repeats in each configuration gave it a menu every time.
- **C, gjs, Python** in the live panel: gnome-text-editor, gnome-characters,
  gnome-music menus open from the panel; nautilus too, with gtk-nocsd's own
  job intact (compiz title bar, no `_GTK_FRAME_EXTENTS`) -
  `merged-nautilus.png`.
- **classtest**: stand-in for `win.class-hello` follows
  `gtk_widget_action_set_enabled()` both ways, activates once when enabled,
  not when disabled - identical to 0.9 separate.
- **Other desktops** (Xvfb, explicit `LD_PRELOAD`): `XDG_CURRENT_DESKTOP=XFCE`
  - menu not hooked ("is not Unity"), application fine; `GNOME` - gtk-nocsd
  unloads itself as designed, our code never runs; `Unity` - hooked.
- The same patch built with upstream's plain `make` (-O0, no
  `-Bsymbolic-functions` - the build that broke 0.8) gave the menu for
  gnome-text-editor, gnome-characters, gnome-music and classtest from the live
  session. papers could not be tried that way: its AppArmor profile refuses
  to map a library from `/home` (`apparmor="DENIED" operation="file_mmap"`);
  installed in `/usr/lib` it works.

Not tested: a Gir.Core application (none in the 26.04 archive) - the
`dlsym()` path should now reach it, but nothing here shows it does; a
statically linked GTK4 (still not handled: the menu code looks for
`libgtk-4.so.1` by name).

## What is still needed to drop the duplicate

1. **Decide where the merged code lives.** Carrying `global-menu.patch` in
   our gtk-nocsd package would end the double hooking for Ubuntu Unity, but
   it moves the duplication into our patch: every gtk-nocsd update has to
   carry a ~1250-line patch (1200 of them a new file, 14 lines touching
   upstream code). The real end of the duplicate is upstream taking it.
2. **Upstream is at 4.8 + 20 commits** (agent A: mostly libadwaita header
   titles; bdeb474 drops the `gtk_widget_set_visible` override). The 14-line
   hook part should rebase easily; not tried.
3. **Upstream will want it generic, not Unity-only.** The menu export itself
   is not Unity-specific - it sets the menubar GTK exports over
   `org.gtk.Menus` with `_GTK_MENUBAR_OBJECT_PATH`, which vala-panel-appmenu
   (XFCE, Budgie) is expected to read as well - not checked here. The switch would need a neutral name
   (env var / GSettings schema, now `UNITY_GTK4_MENU_*` and
   `com.ubuntu-unity.gtk4-menu`) and a desktop list or opt-in.
4. **Style**: upstream is one C file in its own naming and formatting
   (`Uncrustify.cfg`); ours is a second file in kernel style.
5. **May's decision** on talking to the maintainer - issue #1 is not answered.

Until then: `libunity-gtk4-menu0` 0.9 stays what aptly ships.

## target2 state

Left in the experiment state: `libgtk-nocsd0 4.8-1+unity2~menu1`,
`libunity-gtk4-menu0` removed (in `~/.dirty`). Back to the released pair:

    sudo dpkg -i libgtk-nocsd0_4.8-1+unity1_amd64.deb   # from aptly pool
    sudo dpkg -i libunity-gtk4-menu0_0.9_amd64.deb
