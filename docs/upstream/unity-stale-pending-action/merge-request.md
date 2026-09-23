# Draft merge request - not sent

Target: https://gitlab.com/ubuntu-unity/unity/unity, branch `ubuntu/devel`.
Source branch: `mr/stale-pending-action` (one commit, `280719d1` before May's
sign-off), pushed from `packages/unity` once May agrees.

---

**Title:** GnomeSessionManager: only the session manager confirms a pending action

**Description:**

On Ubuntu Unity 26.04 the session runs under cinnamon-session, which does not
call `EndSessionDialog.Open` back after Unity asks it to shut down or restart:
it shows its own dialog. When that dialog is cancelled, Unity's
`pending_action_` is never cleared, and the next request from the session
indicator is mishandled in one of two ways:

1. **The menu stops responding** (release notes, known issue: "shutdown/logout
   menu not working after cancelling"). Confirm *Shut Down* in Unity's dialog,
   cancel cinnamon-session's dialog, and *Shut Down…* in the session menu does
   nothing for the rest of the session. The indicator's `Open(2)` is neither
   `NONE` nor equal to the pending `SHUTDOWN`, and the handler has no `else`.

2. **The machine restarts on one click, with no dialog.** Confirm *Restart*
   in Unity's dialog, cancel cinnamon-session's, then choose *Shut Down…* in
   the menu. indicator-session asks for the restart dialog there (`my_power_off`
   uses `END_SESSION_TYPE_REBOOT`), which matches the pending `REBOOT`, so
   Unity emits `ConfirmedReboot` without showing anything. indicator-session
   connects that signal to `reboot_now` and calls logind's `Reboot`.
   Unsaved work is lost.

The fix accepts the confirmation only from the owner of
`org.gnome.SessionManager` with the pending action; anything else cancels the
stale action and is handled as a new request. Under gnome-session, which calls
back at once with the same action, behaviour is unchanged.

Two new tests in `test_gnome_session_manager.cpp`:

- `StalePendingActionDoesNotBlockRequests` - case 1
- `PendingActionIsNotConfirmedByOtherCallers` - case 2; the request comes from
  a second connection, as the indicator's does

Tested:

- `test-gnome-session-manager`: without the fix 46/48 pass and both new tests
  fail; with it 48/48 pass.
- On an Ubuntu Unity 26.04 VM, both scenarios reproduced with the archive
  package (7.7.1+26.04.20260306-0ubuntu3), screenshots and `dbus-monitor`
  logs; with the fix, the dialog opens in both.

A note on running the suite on 26.04, separate from this change: it does not
build or run as shipped - `-std=c++14` against googletest 1.17 (needs C++17),
`tests/gmockvolume.c` under GCC 15 (`incompatible-pointer-types`), and nux
dereferencing the XF86VidMode mode list, which Xvfb does not provide (Xorg with
the dummy driver works). Happy to send those separately if useful.

Related: the double dialog itself (Unity's, then cinnamon-session's) is a
separate issue, not addressed here.
