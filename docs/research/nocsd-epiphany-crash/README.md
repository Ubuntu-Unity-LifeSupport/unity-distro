# gtk-nocsd main: Epiphany aborts when its Passwords dialog opens

Agent B, 2026-09-26, on `target2` (Unity session, Epiphany 49.2-3ubuntu1,
GTK 4.22.4, libadwaita from resolute). target2 was rolled back to `Clean-2`
afterwards. Found during `research/nocsd-gaps/`. Nothing was sent anywhere.

Our aptly ships gtk-nocsd 4.8, which does not have this bug. It affects
upstream `main` only.

## Result

**First bad commit: `8f076dd` "Disregard window title set from library when
checking if title was set"** (2026-09-20). The commit exists to fix GNOME
Mahjongg: its title was set once with the play time, and then the label was
shown as the time increased.

**Bisect.** gtk-nocsd was built at each of the 21 commits `4.8..main`
(6b1f70a) in the resolute chroot and preloaded into a fresh Epiphany. The
script clicked "Passwords" in the application's own menu; the global menu
was not involved.

- Every commit up to `6a4e428` has no critical, and the Passwords window
  opens.
- `8f076dd` and every later commit have a critical, and Epiphany aborts.
- Confirmed 3 of 3 on `6a4e428` against `8f076dd`.

`tests/epi.sh` does one run.

## Mechanism

`8f076dd` stores the text the library sets as a window title in
`GTKNoCSDSetTitle`. `GTKNoCSDLabelChange` then treats a title equal to it as
"no title set":

```c
bool HasTitle = Title != NULL && (SetTitle == NULL || strcmp(Title,
	SetTitle) != 0);
```

Epiphany's Passwords view is an `AdwDialog` presented in its own
`GtkWindow`. It has no dialog title; its header shows a label of its own,
"Пароли". A debug build logged each call:

1. The header label (class `title`, in an `AdwHeaderBar`) is checked. The
   window title is `''` and `HasTitle` is 1, so the library sets the window
   title to "Пароли" and stores it as `GTKNoCSDSetTitle`.
2. gtk-nocsd's `adw_dialog_present` hook calls
   `GTKNoCSDCheckFirstLabel`. That sets `GTKNoCSDLabelParentCheck = false`
   and checks the first label of the dialog. For an empty password list,
   this is the title of an `AdwStatusPage`, "Пароли не найдены" ("No
   passwords found"): class `title`, no header bar among its ancestors,
   so `Parent == NULL`.
3. The window title equals `GTKNoCSDSetTitle`, so `HasTitle` is now false.
   `!HasTitle && TitleClass` holds, and the branch that sets the title
   runs.
4. The branch calls `gtk_widget_get_preferred_size(Parent, …)` and
   `gtk_widget_set_size_request(Parent, …)` with `Parent == NULL`.
   `get_preferred_size` fails `GTK_IS_WIDGET` with a critical.
5. Epiphany calls `g_log_set_always_fatal(G_LOG_LEVEL_CRITICAL)` unless
   `G_DEBUG` is set (`ephy_debug_set_fatal_criticals`, lib/ephy-debug.c), so
   the critical aborts it. The core dump shows SIGABRT from `g_log` in
   `GTKNoCSDLabelChange` ← `GTKNoCSDCheckFirstLabel` ← `adw_dialog_present`.

**With `G_DEBUG` set**, criticals are not fatal and Epiphany survives, but
the result is still wrong:
- on main: 2 criticals, and the dialog window is titled "Пароли не
  найдены";
- on `6a4e428`: no critical, and the title is "Пароли".

Before `8f076dd`, the window title set in step 1 counted as a title, so the
branch was not entered in step 3.

The unguarded size request is older than `8f076dd`, but not in 4.8. 4.8
sets a title only for labels with `Parent != NULL` and has no size request.
- `9896068` added the size request.
- `bd1c1bc` added the `!GTKNoCSDLabelParentCheck` clause
  (`HasTitle && Title[0] == '\0' && … || !GTKNoCSDLabelParentCheck`).

From `bd1c1bc` on, a dialog whose window title is still empty when its first
label is checked would already reach the size request with `Parent ==
NULL`. `8f076dd` made it reachable in a common case: a dialog whose header
title was just set by the library.

**Under gdb it does not abort.** gdb stops at the critical's `SIGTRAP`;
with that signal ignored, the process continues past it. Use a core dump
(`kernel.core_pattern`, `ulimit -c`) instead. `tests/epigdb2.sh` gives the
stack at the critical.

## Minimal reproducer

`tests/dialogtitle.c` is a libadwaita program that makes criticals fatal, as
Epiphany does. Build:

```
cc dialogtitle.c $(pkg-config --cflags --libs libadwaita-1)
```

It has two modes:
- `dialog`: an `AdwDialog` without a title, presented without a parent,
  with a header bar whose title widget is a `title` label ("Passwords"), and
  an `AdwStatusPage` ("No Passwords Found") as content.
- `clock`: a window whose header title widget is a `title` label that
  changes every 0.4 s, like Mahjongg's clock. It prints the window title.

Measured with `tests/rep.sh`:

| gtk-nocsd | `dialog`, 3 runs | `clock`: window title while the label counts 00:01..00:04 |
|---|---|---|
| none | exit 0 | - |
| `6a4e428` (before) | exit 0, 0, 0; title "Passwords" | stays `00:00`: the Mahjongg bug |
| `8f076dd` | SIGABRT 3 of 3 | follows the label |
| main `6b1f70a` | SIGABRT 3 of 3 | follows the label |
| main + fix | exit 0, 0, 0; title "Passwords" | follows the label |

## Fix

`0001-Keep-the-header-title-of-LibAdwaita-dialogs.patch` applies on main
6b1f70a. It is authored `NeiroNext`, with an `Assisted-by` trailer. It is
formatted with upstream's Uncrustify config and builds with 0 warnings under
upstream's flags.

- It disregards the library's own title only for labels in a header
  (`Parent != NULL`). That is the case `8f076dd` was made for; Mahjongg's
  clock is a header title widget. A label outside a header, such as the
  first label of a dialog, can no longer replace the title the library
  just took from the header.
- It sizes the header only when there is one.

Epiphany with the fix: 3 of 3 alive, no critical, and the Passwords window
is titled "Пароли". The same holds with `G_DEBUG` set. The reproducer's
`clock` mode still follows the label, so the Mahjongg fix is kept.

Not tested on GNOME Mahjongg itself: its board is dealt at random, so a
scripted move could not be placed. The `clock` mode stands in for it.

Whether to report this to the maintainer is May's decision.
