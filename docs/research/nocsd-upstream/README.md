# The global menu as a patch for gtk-nocsd upstream

Agent B, 2026-09-25, on `target2`. Follows `research/nocsd-merge/` (the menu
built into our 4.8 package as a second file). May asked for three things
before deciding whether to offer it to gtk-nocsd's maintainer: port it to
upstream's current code, make the switch desktop-neutral, and write it in
upstream's own style. Nothing was sent anywhere; issue #1 is not answered.

## Result

One commit on upstream `main` 6b1f70a (4.8 + 20 commits, 2026-09-24):
`0001-Export-GTK4-header-bar-menus-to-the-global-menu.patch`, 890 lines added
to `Source/GTK-NoCSD.c` and `README.md`, 1 changed, Makefile untouched.
Local branch `global-menu` in `~/work/b/nocsd-up/src` (6f120dc).

Packaged for testing as `4.8+git20260924.6b1f70a-1+unity2~menu5`
(`packaging.diff`: orig tarball from `git archive main`, the patch,
`Breaks: libunity-gtk4-menu0`, symbols file updated for upstream's own
changes since 4.8 and for the new functions). Built in sbuild, installed on
target2 session-wide. Not in aptly.

## Point 2 - upstream's current code

The mechanical port of `research/nocsd-merge/`'s patch applied to main
without conflicts (offsets only) and worked. It was then rewritten for
points 3 and 4, so what is here is not that port.

## Point 3 - no desktop list

The switch is GTK's own: `gtk-shell-shows-menubar` (XSETTINGS
`Gtk/ShellShowsMenubar`), the setting by which a shell tells GTK that it
shows application menubars itself. Unity's settings daemon sets it (read on
target2: True in the session, False on a bare X server). Which shells read
the `_GTK_*` window properties GTK then sets was checked in their sources:
Unity (indicator-appmenu), vala-panel-appmenu (Xfce, MATE, Budgie) and KDE
Plasma's gmenudbusmenuproxy, all X11 only; LXQt, Cinnamon and GNOME have
nothing that reads them. `GTK_NOCSD_NO_GLOBAL_MENU=1` turns it off, named
like upstream's `GTK_NOCSD_NO_GTK3/4`.

Measured (Xvfb, xsettingsd for the flag): bare X with `XDG_CURRENT_DESKTOP`
Unity or XFCE - nothing exported and nothing added to the window; with the
flag, XFCE and KDE - exported; GNOME - gtk-nocsd unloads itself as always;
flag plus `GTK_NOCSD_NO_GLOBAL_MENU=1` - nothing. Flag switched off while
running - the menubar is withdrawn (no menubar appears inside the window,
`after-off.png`); on again - the next window brings it back; off again -
withdrawn again, process alive.

Dropped against unity-gtk4-menu: the GSettings key `show-application-name`
and the `UNITY_GTK4_MENU_*` variables. Upstream uses no GSettings and no debug
logging; the label is always the desktop entry's name.

## Point 4 - upstream's style

Checked against the README's contribution rules and the code on main, twice,
by a separate reviewer each time:

- Everything in `GTK-NoCSD.c`; `GTKNoCSD` prefix, PascalCase, no
  abbreviations; `//` comments, each function opens with one.
- Only `o_` functions called; the five calls to the library's own
  replacements (`gtk_window_get_titlebar`, `gtk_window_get_child`,
  `gtk_widget_get_parent`, `gtk_widget_get_first_child`,
  `gtk_window_get_application`) carry `// WARNING: Own call`. No new
  `#define`. `G_GNUC_UNUSED` for unused parameters, as upstream does.
- `make format` with Uncrustify 0.78.1 (upstream's main is unchanged by it,
  so this version reproduces their format); no added line over 80 columns;
  `make` with upstream's flags (`-Wall -Wextra -Wconversion`) and Ubuntu's
  (-O2, LTO): 0 warnings; still NEEDED libc only.
- README: one bullet under Options, one short section.
- Commit: imperative subject, one-line body.

Changes the first review asked for, all made: nothing in the constructor -
windows are hooked from `GTKNoCSDGetReferences` once GTK4 and its types are
known, which every GTK4 process passes through `g_object_new` or
`g_module_symbol` before a window exists; no work added to `dlsym` or
`g_module_symbol` beyond one `GET_SYMBOLS` entry; menu-only functions loaded
lazily in their own function, not at every process start; the library's
menubar held by a weak pointer; no `typedef`, `enum` or `__sync`; no
fixed-size string buffers. The second review found the library opened GTK4
by a fixed name (fatal where upstream finds it by path or statically linked)
and a weak-pointer slip on re-attach; both fixed, the second tested.

## Measured on target2 (final build)

- Session after reboot: panel, unity-settings-daemon, nemo-desktop,
  indicators up; no crash report; error log sources the same as before.
- 18 GTK4 applications (the `breadth` set): menu exported for all 18, and
  the per-item audit is identical to the two-library setup except the
  stand-in prefix, now `gtk-nocsd-` (`breadth-upstream-main.txt`).
- classtest: stand-in follows `gtk_widget_action_set_enabled` both ways,
  activates once when enabled.
- Live panel: gnome-text-editor, gnome-characters menus open from Unity's
  panel, "About" chosen there opens the About window.

**A failure on the way, recorded because the partial check missed it.**
Round two moved `gtk_menu_button_get_type` to the lazy loader but left its
`GET_TYPE` in `GetReferences`, where it ran first: every menu button type
was 0, and all 18 applications lost their menu. classtest alone would not
have shown it; the full set did. Fixed by fetching the three types in the
lazy loader. Also: right after a reboot four applications showed no window
properties within the 7 s the audit waits; three repeats of each were
clean, and the full set run once the machine had settled was 18/18.

## Not done, and why

From the second review, left as they are, and they would be the first
questions a maintainer might ask:

- Items whose actions come from `gtk_widget_insert_action_group` (prefixes
  other than `app.`/`win.`) are exported but do nothing. unity-gtk4-menu
  behaves the same.
- The exported menu is a copy made when the first window is realized; later
  changes to the menu, and other windows' different menus, are not followed.
  One menubar per application is GTK's own model.
- A plain `GtkWindow` (not `GtkApplicationWindow`) has no window action map
  for stand-ins.
- Flag switched on at runtime: exported from the next window, not the open
  ones.
- Replacing `realize` in the window classes is a mechanism gtk-nocsd itself
  does not use. See "Why realize is replaced" below.
- Gir.Core and statically linked GTK4 are untested (no such application in
  26.04).

## Why realize is replaced in the window classes

May asked whether this is a crutch. What gtk-nocsd does to reach every window
is an emission hook on GtkWindow's `map` signal (`GTKNoCSDHooker`) - its job
happens when a window is shown. The menu has to be set earlier: GTK
publishes the `_GTK_MENUBAR_OBJECT_PATH` window property while the window is
realized, and only if the application has a menubar by then.

Measured 2026-09-25: the same patch with an emission hook on `realize`
instead of the class replacement (`o_g_signal_add_emission_hook`, as
`GTKNoCSDHooker` does) gave the menu to none of 17 applications of the
breadth set (classtest alone got it). An emission hook runs after a
`G_SIGNAL_RUN_FIRST` signal's class handler, i.e. after the window has
already published its properties.

Replacing `realize` in the classes of `GtkWindow` and `GtkApplicationWindow`
is what appmenu-gtk-module, the GTK3 global menu Ubuntu ships, has always
done (`packages/appmenu-gtk-module/src/hijack.c`, `hijacked_window_realize`,
lines 287-292), and what unity-gtk4-menu copied. Its known limit: a window
subclass whose class was initialised before the replacement keeps GTK's
original realize. Here the replacement happens when gtk-nocsd first fetches
GTK4's types, before an application creates its first window; none of the
18 applications hit the limit.

## For point 1 (May's decision)

What the patch is and is not:

- It is complete, builds clean, follows the written rules and matches the
  two-library behaviour on everything we test.
- It is large (890 lines) for a project whose history is one author's small
  commits, and it adds a feature outside "remove CSD". The maintainer said
  he was asked for this for Xfce and might do it himself; a patch from us is
  an offer of a finished implementation, which he may still prefer to write
  his own way.
- It is AI-written, and he has already noticed that in our commits
  ("Not sure what to comment on rehashing my code with LLM"). The commit
  carries `Assisted-by: LLM Claude Opus 5.5` as our CONTRIBUTING-UPSTREAM
  rule asks; no upstream commit has such a trailer.
- Author identity: the commit is authored "Ubuntu Unity Life Support";
  what goes out has to be May's name and Signed-off-by, per our rules.
- Testing he asks of contributors is concrete and per application; we have
  Unity only. Xfce/KDE were exercised with a fake XSETTINGS flag under Xvfb,
  not a real panel.

Options, as seen from here: (a) answer issue #1 with the finding that the
segfault was ours and fixed, and offer this patch as a starting point; (b)
answer with the finding only and ask whether he wants the feature in
gtk-nocsd before sending code; (c) keep carrying unity-gtk4-menu 0.9 and say
nothing yet. The patch does not have to be sent to be useful: the same code
can ship as our gtk-nocsd patch if the answer is slow.

## target2 state

`libgtk-nocsd0 4.8+git20260924.6b1f70a-1+unity2~menu5`,
`libunity-gtk4-menu0` removed (all in `~/.dirty`). Back to the released pair:
`dpkg -i` gtk-nocsd `4.8-1+unity1` then unity-gtk4-menu `0.9` from aptly's
pool.
