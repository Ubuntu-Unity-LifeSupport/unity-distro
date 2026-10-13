# A real session start through /etc/X11/Xsession under dash with gtk-nocsd 4.8-1+unity4 (UNITY-20261013-001)

Owner: agent B (target2). Observation record; no package change.

```yaml
task: UNITY-20261013-001
from: UNITY-20261012-005 (gtk-nocsd 4.8-1+unity4, the preload by path)
question: does a session started through /etc/X11/Xsession (#!/bin/sh = dash) come up with the path-form
          LD_PRELOAD that 51gtk-nocsd writes? Until now that path was covered by the build-time test only
          (debian/test-51gtk-nocsd.sh); on target, sessions went through lightdm-session (bash).
result: PASS - the session comes up, the path form with a literal $LIB everywhere, both libraries mapped, no
        ld.so line; the opt-out file works on this path
status: observation recorded; target2 back on Clean-2
```

## Where it ran

- **target2:** restored to Clean-2 and confirmed inside, then the live archive (Release Date 2026-10-13
  00:03:25 UTC) and a full-upgrade (logs/01).
- **Packages:**
  - libgtk-nocsd0 4.8-1+unity4 (`/etc/X11/Xsession.d/51gtk-nocsd` sha256 `ec486e45714c5177…`);
  - libunity-gtk4-menu0 0.10, which is now live;
  - lightdm 1.32.0-6ubuntu4+unity2, unity +unity13, x11-common 1:7.7+26ubuntu1, dash 0.5.12-12ubuntu3.
- **Shells:** `/bin/sh` is `/usr/bin/dash`, and `/etc/X11/Xsession` starts with `#!/bin/sh`.
- **Libraries:** both are `-rw-r--r--`. Both `environment.d` files have the `/usr/$$LIB/` form.
- **Login:** autologin of user mike into `unity`. lightdm's effective `session-wrapper` is
  `/usr/sbin/lightdm-session` (from the system's `lightdm.conf.d`: `01_debian.conf`, `02_ubuntu.conf`,
  `50-autologin.conf`).
- **Applications:** gnome-disks 46.1 (GTK3) and gnome-calculator 50.0 (GTK4) were installed from the archive.

## Method

Two test files, written by `testfiles.sh`:
- **`/etc/lightdm/lightdm.conf.d/99-b1301-xsession.conf`:** `[Seat:*] session-wrapper=/etc/X11/Xsession`.
  lightdm then runs `/etc/X11/Xsession /usr/bin/unity-session`.
- **`/etc/X11/Xsession.d/98zzb1301trace`:** a trace sourced by the Xsession script. It sits after
  `95dbus_update-activation-env` and before `99x11-common_start`, which execs the session. It records the
  executable of the shell that sources it (`/proc/$$/exe`) and its `LD_PRELOAD`.

Each session is a cold boot (poweroff over ssh, then `start_vm`), so the user manager is new each time.
`check.sh` then records over ssh:
- lightdm's command line and the trace;
- the user manager's value (`systemctl --user show-environment`);
- the session process, which is lightdm's session child's child, i.e. what the wrapper became by exec. Also
  compiz and unity-panel-service: `LD_PRELOAD` with `cat -A` and the two libraries in `/proc/PID/maps`;
- gnome-disks started through the user manager (`systemd-run --user`), and gnome-calculator started from the
  session process's environment, the same two readings for each;
- `sudo -n true`, `su -c true`, `ping -c1` and `pkexec true` run with the session's value: ld.so lines on
  stderr;
- `ld.so: object` lines in the system and user journals of the boot.

## Results

| session | wrapper (lightdm.log) | trace: shell | `LD_PRELOAD` in the user manager, session, compiz, panel, GTK3, GTK4 | maps | ld.so lines (4 programs, journals) |
|---|---|---|---|---|---|
| s0 control (logs/03) | `/usr/sbin/lightdm-session` | `/usr/bin/bash` | `/usr/$LIB/libunity-gtk4-menu.so.0:/usr/$LIB/libgtk-nocsd.so.0` | both, in all six | 0 |
| **s1 (logs/05)** | **`/etc/X11/Xsession`** | **`/usr/bin/dash`** | the same, literal `$LIB`, no `/usr//`, no `$'` in the process environments | both, in all six | 0 |
| s2, opt-out file (logs/07) | `/etc/X11/Xsession` | `/usr/bin/dash` | `/usr/$LIB/libunity-gtk4-menu.so.0` only | libunity-gtk4-menu only | 0 |

- **The user manager.** `systemctl --user show-environment` prints `$'/usr/$LIB/…'`. That is how `systemctl`
  quotes a `$`; the environment generator gives the same value (`/usr/\$LIB/…`).
- **Every session came up.** The Unity desktop shows in a vbox screenshot after s1. gnome-calculator's window has
  `_GTK_MENUBAR_OBJECT_PATH` in all three sessions.
- **The opt-out file** in s2 (`~/.config/environment.d/50-gtk-nocsd.conf`, empty) turns gtk-nocsd off on this
  path, as UNITY-20261012-005 found for the lightdm-session path:
  - the Xsession trace, the user manager and every process have only unity-gtk4-menu;
  - gtk-nocsd is not mapped.
- **`~/.xsession-errors`** has `dbus-update-activation-environment: setting LD_PRELOAD=…` with the same value in
  each session, and no ld.so or preload error.

## Cleanup

`testfiles.sh off` and `optout-off` removed the three test files, and lightdm was back to
`/usr/sbin/lightdm-session` (logs/08). Then target2 was restored to Clean-2 and confirmed inside (logs/09):
- no `~/.dirty`, no `~/b1301`, no `~/.config/environment.d`;
- only `ubuntu.sources`;
- `lightdm.conf.d` holds only the system's three files, and no test file is in `Xsession.d`;
- the archive's gtk-nocsd.

target2 is powered off.

## Notes

- `/var/log/lightdm/lightdm.log` kept the lines of the earlier boots, so each check shows the last few
  `Running command` lines. The newest is the boot's own; the boot times are in each log's first line.
- No independent Verifier was run, at the owner's discretion for a measurement task (C, 2026-10-13). Nothing
  broke.
