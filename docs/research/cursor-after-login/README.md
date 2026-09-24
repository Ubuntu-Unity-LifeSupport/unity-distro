# Known issue #1: the cursor disappears after login

Release-note workaround: `sudo systemctl restart lightdm`.

## Candidate mechanism - the cursor plugin of unity-settings-daemon

`plugins/cursor/gsd-cursor-manager.c`, `gsd_cursor_manager_start()`:

    /* Start by hiding the cursor, and then initialising the default
     * root window cursor, as the window manager shouldn't do that. */
    set_cursor_visibility (manager, FALSE);

The plugin hides the pointer (`XFixesHideCursor`) as soon as the session
starts, and shows it again only when a per-device idle monitor
(`gsd_idle_monitor_add_user_active_watch`) reports a non-touchscreen device
as active. If that report does not come - the plugin's only way back - the
pointer stays invisible for the session while the mouse keeps working, and a
new session (restart LightDM) gets another roll of the dice. That matches
the issue and its workaround.

Public history (rule 0): LP #1390628 "Mouse pointer invisible after upgrade
to Ubuntu 14.10 and 15.04" (unity-settings-daemon, Confirmed, 38 comments,
workaround: disable the cursor plugin or restart the session); Debian
#755050, the same plugin in gnome-settings-daemon, same workaround, no root
cause. gnome-settings-daemon later dropped the plugin altogether.

## What we measured

- Not reproduced on our VirtualBox target: we never saw a missing pointer
  there. All four pointer devices are `mouse` to GDK, none a touchscreen.
- `usd-cursor-debug-before.txt`: archive `0ubuntu6` logs "Attempting to hide
  the cursor" at start, and nothing shows it again while the mouse is not
  touched. Our own input goes through XTEST, which the plugin ignores - so
  automation cannot tell whether the monitor would have fired.
- `usd-cursor-debug-after.txt`: with the fix the plugin starts and does not
  hide the pointer.

## The fix - unity-settings-daemon `15.04.1+21.10.20220802-0ubuntu7+unity1`

Don't hide on start; hide only when a touchscreen becomes the active device
(unchanged). Built on `ubuntu/devel` (`0ubuntu7`, unreleased: fixes the build
with the current toolchain and moves to debhelper), plus a packaging fix:
the move made the build run `make check`, and `gcm-self-test` needs a display
- now under `xvfb-run`. Regression check on target against `0ubuntu6`: the
same 20 plugins active, logind inhibitors held, power key shows Unity's
dialog, no crash reports.

**Whether it fixes #1 on the machines that have it is not proven** - the
mechanism is read from code and matches, but the bug did not reproduce here.
A person seeing a missing pointer after login with this package installed
would disprove it.
