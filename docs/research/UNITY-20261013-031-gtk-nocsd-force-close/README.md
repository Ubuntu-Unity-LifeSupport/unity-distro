# UNITY-20261013-031: force-closing a popped-out dialog emits "closed" (gtk-nocsd 4.8-1+unity6)

Agent A, target `target-desktop`.

## What was wrong

gtk-nocsd presents a libadwaita AdwDialog in a window of its own. For such a
dialog libadwaita's `adw_dialog_force_close` only closes the window:
`closed` is not emitted and the dialog keeps its reference to the closed
window. An embedded dialog (without gtk-nocsd) emits `closed` when it is
force-closed.

Epiphany 49.2-3ubuntu1 keeps its preferences dialog until `closed` and
force-closes it when preferences are opened from another window. On
target-desktop (2026-10-17), the sequence "Preferences in window 1, a new
window, Preferences from window 2, Preferences again" made epiphany abort
(exit 134; with 4.8-1+unity5 on a `GLib-GObject-CRITICAL ... instance with
invalid (NULL) class pointer`, which epiphany makes fatal) with
gtk-nocsd 4.8-1+unity4 and 4.8-1+unity5 preloaded; without any preload it
exited normally (143). A library preloaded before gtk-nocsd that replaced the
force-close of such a dialog with a close that emits `closed` made the same
sequence pass (2 of 2).

## What is fixed

| package | version | change |
|---|---|---|
| gtk-nocsd | 4.8-1+unity6 | `debian/patches/0002-emit-closed-when-a-popped-out-dialog-is-force-closed.patch` and build-time tests; branch `a/UNITY-20261013-031` (`0845602`, `bcc6523`, `e42e03a`) on the published +unity5 `6aab167`. |

- In gtk-nocsd's `adw_dialog_force_close` hook, a dialog that is the content
  of its own window (popped out by gtk-nocsd) is closed the way 0001 closes a
  dialog whose parent window is destroyed: `closed` is emitted once, also when
  `can-close` is FALSE, and `can-close` is restored afterwards. The dialog can
  be presented again.
- Embedded dialogs (for example from `adw_alert_dialog_choose`, which
  libadwaita presents itself) and dialogs that were never presented are
  force-closed as before.
- No new GTK function is hooked and no symbol is added.

## Checks

- **Build-time tests** (one process per case, under `xvfb-run` with the built
  library preloaded): a dialog kept by the application and force-closed
  (F1: `closed` once, presented again), a single-instance dialog cleared on
  `closed` (F2), `can-close` FALSE (F3), force-close from a `close-attempt`
  handler (F4). Built without 0002 (`0845602`) F1-F4 fail; with it all pass.
  Controls pass on both: a dialog never presented, force-close from a `closed`
  handler, an embedded dialog of `adw_alert_dialog_choose`; the cases of 0001
  still pass.
- **Target** (`dev/target/`): libgtk-nocsd0 4.8-1+unity6 from `build/` on the
  live stack (unity +unity14, light-locker +unity5, unity-gtk4-menu 0.13),
  cold boot, the session's preload: the epiphany sequence above 3 of 3 without
  abort (exit 143 at the end, no crash report). The checks of
  UNITY-20261013-029 still pass: SIGTERM with the default-browser question
  open 5 of 5 exit 143; preferences opened, closed and opened again 3 times.

## Verification

- Design and code review (Design Challenger): APPROVE in round 2. Round 1 asked
  to tell popped-out dialogs from embedded ones by the window's content, not
  by having a window ancestor.
- Verifier: see the release record.

## Not changed / known limits

- For embedded dialogs the hook still removes the application window from
  gtk-nocsd's own window list after a force-close (as before).
- A host window unrealized before it was mapped is not closed by
  `gtk_window_close` (as with libadwaita's own force-close).
