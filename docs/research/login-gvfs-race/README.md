# Login race: gvfs blocked for two minutes, desktop black

Found while checking logout (`research/compiz-restart/`, "Logging out"). Fixed
in unity-session `49.4+unity1`, in aptly,
https://github.com/Ubuntu-Unity-LifeSupport/unity-session.

## Symptom

After some logins the desktop stays black - no wallpaper, no icons, panel and
launcher fine - for about two minutes. nemo-desktop, zeitgeist and Unity's
session proxies log D-Bus timeouts; at +120 s dbus-daemon logs
`Failed to activate service 'org.gtk.vfs.Daemon': timed out
(service_start_timeout=120000ms)` and everything recovers. On target: 3 of
13 logins with the archive unity-session (cycles 1 and 4 of the logout test,
Ai-1 below); the first login after a boot was not among them, but nothing
makes it immune.

## Cause

`/usr/libexec/run-systemd-session` (unity-session, started by `unity-session`
for every Unity login) begins with

    # stop any lingering active units from a previous session
    systemctl --user stop graphical-session.target graphical-session-pre.target

At the same moment `ibus-daemon`, started from Xsession by im-config,
activates gvfs over D-Bus. gvfs-daemon is `PartOf=graphical-session.target`.
Stopping a target that is **not running** still stops the units that are
PartOf it and are being started right now; systemd kills gvfs-daemon's start,
dbus-daemon is never told, and keeps the activation pending until its 120 s
timeout, with every gvfs client waiting behind it.

Timestamps from a login with the stop instrumented (`runs/02-cycles-A-Ai-B.txt`, Ai-1):

```
23:19:00.860  dbus-daemon: Activating via systemd: org.gtk.vfs.Daemon   (ibus-daemon)
23:19:00.877  systemd: Starting gvfs-daemon.service
23:19:00.971  run-systemd-session: stop begin
23:19:00.991  systemd: Stopped gvfs-daemon.service
23:19:01.009  run-systemd-session: stop end
      +120 s  dbus-daemon: Failed to activate service 'org.gtk.vfs.Daemon': timed out
```

In the other two instrumented logins the stop came 15 ms *before* ibus's
request and nothing happened: a race with a window of milliseconds. Making
gvfs-daemon slow to start (`ExecStartPre=/bin/sleep 3`, cycles A) did not
widen it - what matters is whether the request lands before or after the stop.

Deterministic model (`runs/racetest.sh`, `runs/00-racetest-output.txt`): a
D-Bus activated unit, PartOf an inactive target, slow to start. Activation
alone: 2.3 s. Stop the inactive target 0.5 s into the activation: the unit is
killed with SIGTERM, the D-Bus call returns after **120.0 s**. Stop only if
the target is active: 2.3 s.

## Fix

Stop the two targets only when one of them is not inactive - when there is
something left from a previous session to stop. After a normal logout both are
inactive (measured in every patched login, `targets: inactive inactive`), so
a normal login no longer stops anything.

Measured: 6 logins with `49.4+unity1` (cycles B, root-driven through
`systemd-run` as in the logout test, so the user manager was fresh each time):
no stop issued, no activation timeout, desktop drawn. In two of them (B-2,
B-5) ibus's request came before the check - the window in which the old
script killed gvfs.

Left as it was: when a previous session ended without stopping its targets (a
crash of the session itself), the targets are active and still get stopped,
with the same race possible - rarer, and the stop is then needed.

## Not this bug

The two minutes of black screen agent B saw on `oem-test` at the first
Unity login after an OEM install: that boot's journal has no gvfs stop and no
activation timeout; it is a slow first start (autologin 18:54:31, compiz
loading plugins 18:55:22; compiz-profile-selector took ~19 s).

## Rule 0

The script is Ubuntu's old gnome-session `run-systemd-session` (bionic era),
unchanged in unity-session since 2025 (`git log`); a web search for the
script and the race found nothing about it.
