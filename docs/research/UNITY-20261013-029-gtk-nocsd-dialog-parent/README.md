# UNITY-20261013-029: Epiphany aborts on SIGTERM with gtk-nocsd (gtk-nocsd 4.8-1+unity5)

Agent A, target `target-desktop`; reproduction also on `target-desktop-2` (agent B).

## What was wrong

gtk-nocsd presents a libadwaita AdwDialog in a window of its own, transient for
and modal over the parent window, and adds the parent's application and window
as the dialog's `app` and `win` action groups. When the parent window was
destroyed, the dialog's window stayed open as a toplevel and kept the dialog,
the parent window and the application alive. Without gtk-nocsd the dialog is
embedded in the parent window and goes with it.

Epiphany 49.2-3ubuntu1 asks on start whether it should become the default
browser (an AdwAlertDialog) when it is not the default. Ended with SIGTERM while
that question was open, it still held its shell object after
`g_application_run` returned and aborted on its own check
(`ephy-main.c:459: assertion failed: (!ephy_shell)`), leaving a crash report. A
session's logout ends running applications with SIGTERM.

- target2, from a clean install with epiphany installed (B): with
  libgtk-nocsd0 4.8-1+unity4 preloaded (the session's preload, or gtk-nocsd
  alone) 9 of 9 runs aborted; without any preload 0 of 6 (exit 143). Raw data
  outside this repository.
- target-desktop: the same with the question shown (Firefox the default http
  handler): exit 134 with gtk-nocsd, 143 without.
- The mechanism was measured with a library preloaded before gtk-nocsd that
  logged when the objects were finalized: at SIGTERM the parent window was
  unrealized but never disposed, and the dialog and its window were never
  finalized. Removing both action groups, or closing the dialog when its
  parent is destroyed, gave exit 143 with all three finalized.

## What is fixed

| package | version | change |
|---|---|---|
| gtk-nocsd | 4.8-1+unity5 | `debian/patches/0001-close-popped-out-dialogs-with-their-parent.patch` and a build-time test; branch `a/UNITY-20261013-029` (`970c4c8`, `590f2a4`, `6aab167`) on the published +unity4 `a4ec25e`. |

- When a dialog is presented on a parent window, gtk-nocsd connects to the
  parent's `unrealize` (once per parent and dialog, until the dialog goes). If
  the parent is no longer among the toplevel windows, that is, it was destroyed
  and not only unrealized, and the dialog is still in a window transient for it,
  the dialog is closed: `closed` is emitted once, also when `can-close` is
  FALSE, and `can-close` is restored afterwards.
- No new GTK function is hooked: libgtk-4 binds its own calls directly, so a
  hook on `gtk_window_destroy` would miss GTK's own close path (window manager,
  Ctrl+W). Six new internal function pointers are exported, as the existing
  ones are (`debian/libgtk-nocsd0.symbols`).
- GTK3 programs are not affected (the code runs only from the libadwaita hook).

## Checks

- **Build-time test** (`debian/tests-src`, run under `xvfb-run` with the built
  library preloaded, one process per case): an application whose window is
  destroyed or closed (T1, T1b), a plain window (T2), a dialog on a dialog
  (T3), a dialog kept by the application and presented again (T4),
  `can-close` FALSE (T5), two dialogs on one parent (T6). The application,
  windows and dialogs must be finalized and `closed` emitted once. Built without
  the fix (`970c4c8`) T1-T6 fail and the four controls (dialog closed first,
  presented again after a close, a hide-on-close parent, a GTK3 program) pass
  (`dev/red-on-base-tests.txt`); with the fix all pass (`build/`).
- **Target** (`dev/target/`): epiphany with the question open, the session's
  preload, SIGTERM after 15 s: 5 of 5 exit 143, no crash report; the question
  open in its own window before the SIGTERM (screenshot); Preferences opened,
  closed and opened again three times. Not tested on target: closing the main
  window through the window manager while the question is open (the window
  manager closed the modal question instead, with and without the change; the
  build-time T1b closes the main window), and Preferences in a session with two
  windows.

## Verification

- Design and code review (Design Challenger): APPROVE in round 2. Round 1 asked
  for the `unrealize` check instead of a `gtk_window_destroy` hook, and for
  `adw_dialog_close` instead of `adw_dialog_force_close`, which for a dialog in
  a window of its own emits no `closed`.
- Verifier: PASS. An independent rebuild of `6aab167` in the same chroot gave
  bit-identical source and binary packages.

## Not changed / known limits

- gtk-nocsd's own `adw_dialog_force_close` wrapper has the same missing
  `closed` for popped-out dialogs: UNITY-20261013-031.
- A parent destroyed without ever having been realized emits no `unrealize`;
  its dialog keeps the old behaviour.
- In one run on target-desktop, epiphany without any preload also aborted when
  ended with SIGTERM while its Preferences dialog was open, on a critical
  (`g_object_unref: assertion 'G_IS_OBJECT (object)' failed`) that epiphany
  makes fatal. That is not changed here.
