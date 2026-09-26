# Known issue #1: the cursor disappears after login

**Status 2026-09-26: reproduced, cause found and fixed in unity-settings-daemon
`0ubuntu7+unity4` (in aptly).** The measured account is the section "Reproduced
and fixed" at the end; the sections before it are the 2026-09-24 reading of
the code, kept as written - its mechanism was incomplete and its fix
(`+unity1`) has been reverted.

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

## Corroboration from the release notes (host session, 2026-09-24)

The Ubuntu Unity 26.04 release notes describe #1 more precisely than our list:
after login the pointer is not drawn, **but elements under it still highlight
on hover** - the pointer exists and moves, only its image is missing. That is
exactly what `XFixesHideCursor` does, and not what a broken input device or a
crashed compositor would look like. It strengthens the cursor-plugin mechanism;
it is still not a reproduction.

## Reproduced and fixed (2026-09-26, agent A)

### Rule 0

- Source of the release-notes entry: gitlab.com/ubuntu-unity/issue-tracker
  work item #161 "Cursor sometimes invisible" (2026-03-31, labels 26.04 and
  Regression, open, no comments): "sometimes right after login ... not visible
  but can click and highlight", QEMU and a ThinkPad R61. Nothing on Launchpad
  for 26.04; LP #1390628 (2014-2016) is the same symptom, never explained.
- Newer versions: 26.10's `26.10.1ubuntu` has the same code; upstream GNOME never
  had this copy of the idle monitor (below). Nothing to take.

### How it was measured

Real input without a person: `tools/evinject.py` / `evabs.py` write
`input_event`s into the **existing** evdev node of the PS/2 mouse or the USB
tablet, so the X server sees the device it had at login move - not XTEST
(which the plugin ignores) and not a new uinput device. Device nodes are found
**by name**: `eventN` numbers change between boots, and the first series
(`runs/series-a-0ubuntu6-WRONG-DEVICE.log`) partly wrote into the Video Bus
keyboard - its "failures" are not evidence. What the plugin decided comes from
its own debug log: for the test, `unity-settings-daemon` was diverted to a
wrapper running the real binary with `--debug` into `/tmp/usd-PID.log`
(removed afterwards). A VirtualBox screenshot cannot show the pointer (the
host draws the hardware cursor), so visibility is taken from the plugin's
`Attempting to hide/show` and confirmed by the cause below.

### Cause

1. **The daemon is started twice per login.** `unity-session.target` wants
   `unity-settings-daemon.service`, and systemd's xdg-autostart generator also
   starts `/etc/xdg/autostart/unity-settings-daemon.desktop` as
   `app-unity-settings-daemon@autostart.service`. One of the two exits on the
   taken name; which one survives varies.
2. **On the way they race for `org.gnome.Mutter.IdleMonitor`.**
   `gsd-idle-monitor.c` added the X event filter that dispatches XSync alarms
   to *every* idle watch in `on_bus_acquired` and **removed it in
   `on_name_lost`**. When the survivor loses the name and gets it back, the
   filter stays removed: no idle or user-active watch in the process fires
   again.
3. **The cursor plugin hid the pointer at start** and shows it only when a
   pointer device's user-active watch fires - which now never happens. The
   pointer moves and highlights what it passes over, invisibly, for the whole
   session; restarting LightDM rolls the dice again.

Proof on a live failing session (boot a10): real PS/2 and tablet input moved
the pointer, the plugin stayed hidden; `gdb` calling
`gdk_window_add_filter (NULL, xevent_filter, NULL)` into the process and one
more movement gave `Device 12 ... became active` / `Attempting to show`.

History (subagent, from the git-ubuntu import): the D-Bus idle monitor was
copied from mutter 3.10 in `f88f984` (14.10, LP #1377847); `6fca738` (LP
#1380278) made the removal in `on_name_lost` actually match. mutter never tied
its alarm handling to the name; upstream gnome-settings-daemon never had this
copy. Also found: in `0ubuntu7` (our base since `+unity1`) and 26.10 the move
to debhelper left libexecdir at `/usr/libexec` while installing to
`/usr/lib/unity-settings-daemon`, so the autostart entry pointed at nothing -
which by accident started the daemon once and hid this bug in our packages,
while also breaking `localeexec`, `unity-fallback-mount-helper`'s autostart and
the backlight/Wacom LED polkit actions.

### Numbers

| Package | Logins | Survivor lost the name | Pointer stayed hidden after real input |
|---|---|---|---|
| archive `0ubuntu6` (series c, `runs/series-c-0ubuntu6.log`) | 12 | 2 (c6, c8) | **2** (c6, c8) |
| archive `0ubuntu6`, earlier series, rows with the name lost | a3, a10 | 2 | 2 (a10 re-tested with the right device, then fixed live with gdb) |
| `0ubuntu7+unity4` (series f, `runs/series-f-unity4.log`) | 12 | 0 (one instance every time) | **0** |

Deterministic reproducer `tools/repro1.sh` (restart the daemon so the plugin
hides, take the name away for 2 s with `tools/steal-idle.py`, move the
mouse): archive 3/3 stays hidden, control without the steal 1/1 shown;
`+unity4` 3/3 shown although the name is lost and regained the same way.
All logins autologin, cold boot, VirtualBox, `lightdm-gtk-greeter` configured
(the stock 26.04 Unity setup uses it, not unity-greeter). Not tested: a
password login through the greeter, a second login in the same boot, real
hardware - the mechanism does not depend on any of them, the start-up race does.

### Fix - `15.04.1+21.10.20220802-0ubuntu7+unity4`

- `idle-monitor: keep the X event filter when the D-Bus name is lost` (the cause).
- `Start the daemon once per session: from the systemd user unit` (unit runs
  `localeexec`; autostart entry `X-systemd-skip=true`).
- `debian: install the helpers where their callers look for them` (libexecdir).
- Revert of `+unity1`'s cursor change - the plugin hides until a mouse is used
  again, as in the archive.

After it, on target: one `unity-settings-daemon`, no `Lost or failed to acquire`
and no `Name taken` in the journal, `unity-fallback-mount-helper` running,
polkit's backlight helper path `/usr/lib/unity-settings-daemon/usd-backlight-helper`.

### Follow-up 2026-09-26: the paths not tested before (`+unity4`)

Two test users with a known password (`utest`, `utest2`, created for this;
mike's password stays unknown), autologin off, the greeter showing a manual
login field; keyboard into the greeter through XTEST (before the user's
session exists, so the plugin is not involved), mouse after login through the
PS/2 evdev node as before. Per boot (`tools/greeter-boots.sh`,
`runs/series-GRS-unity4.log`, measured by `tools/cursor-loop2.sh`):

| Path | Runs | One daemon instance | Name lost | Pointer shown after real input |
|---|---|---|---|---|
| G - cold boot, password login through lightdm-gtk-greeter | 12 | 12 | 0 | **12** |
| R - log out (SessionManager.Logout) and log in again, same boot | 11 | 11 | 0 | **11** |
| S - switch user (`dm-tool switch-to-greeter`), second X server `:1` | 12 | 12 | 0 | **12** |

R4 is not counted: that logout did not happen (same daemon PID as G4), so it
measured the G4 session again. Not tested: real hardware.
