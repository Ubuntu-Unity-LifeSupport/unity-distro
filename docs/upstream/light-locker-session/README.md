# light-locker: crash on login under a systemd user session

Status: **ready**, not sent. Second in the queue, after `nux-pcre2`.

## What this is

light-locker aborts on every login on Ubuntu Unity 26.04 - known issue #5 in
the release notes, "light-locker seems to crash on login but login works".
It is two stacked aborts with one cause: light-locker is started by
cinnamon-session, which runs as the systemd user service
`unity-session.service`, so it lives outside the logind session scope and
inherits neither a session nor LightDM's `XDG_SESSION_PATH`.

Two patches, one per abort:

- `0003-Follow-the-user-s-display-session-outside-a-session-.patch` - when
  logind cannot map the PID to a session, use the user's display session
- `0004-Find-the-LightDM-session-when-XDG_SESSION_PATH-is-mi.patch` - when
  `XDG_SESSION_PATH` is missing, ask LightDM for the user's session over D-Bus

Package: `light-locker 1.8.0-3ubuntu4+unity2`, source at
https://github.com/Ubuntu-Unity-LifeSupport/light-locker, branch
`unity/resolute`.

## Where it goes

**Launchpad, not upstream.** Upstream light-locker has been inactive since
2020, with PRs unmerged for years; a merge request there would sit. The route
is the Ubuntu package.

1. Post `bug-report.md` on **LP: #2038808**, an automatic crash report for
   `init_session_id` with no analysis so far, and attach both patches. Turning
   an empty automatic report into a diagnosed bug with a proven mechanism is a
   contribution on its own, before any upload.
2. Nominate it for Resolute, like the nux SRU, if it is to be fixed in 26.04
   rather than only in the development series.

Debian carries the same 1.8.0 and could take the patches too, but the failure
needs a session manager running as a user service, which is an Ubuntu Unity
arrangement. Ubuntu first.

## Re-check before sending

Written 2026-09-23. Run all five - a deferred draft is re-verified, not re-read:

- [ ] Has resolute or the development series received a newer light-locker?
      `rmadison -u ubuntu light-locker`
- [ ] Has anyone commented on or triaged LP: #2038808 since?
- [ ] Is **LP: #2167241** (light-locker crashing when Plasma opens) the same
      mechanism? If so, mention it; if it is a duplicate, say which way.
- [ ] Do both patches still apply to the current source package?
- [ ] Does the crash still reproduce on the current `Clean-updated` snapshot?
- [ ] Does every evidence file still say which boot it came from, and do the
      boot time, `journalctl -b` and any file dates agree? Re-collected
      evidence gets a fresh header, not the old one.

## Evidence

| File | Shows |
|---|---|
| `01-crash-on-clean-system.txt` | the abort on a clean, updated system, and why the stale crash file is not the evidence |
| `02-mechanism-logind.txt` | `GetSessionByPID` failing for a user service and working inside the scope; logind's display session gives the same path |
| `03-launch-chain.txt` | `unity-session.service` -> `cinnamon-session` -> light-locker, and the NotShowIn side note |
| `04-sd-login-from-user-service.txt` | the sd-login calls from light-locker's context, including the `-EINVAL` that undermines PR #153 |
| `05-after-fix-alive.txt` | alive after login, no fatal messages, owns the ScreenSaver name |
| `06-lock-works.txt` | locking switches to the greeter in unlock mode; unlock verified by hand, corroborated by the LightDM log |
| `07-build.txt` | clean build, both patches applied, no new compiler warnings |

Screenshot: `../../screenshots/2026-09-23-light-locker-locked.png`.

Every file opens with the boot, or build, it was taken from and what was
installed at the time. `02` was re-collected on 2026-09-23 because the first
version came from a boot that also had our GTK4 shim installed, and did not
say so.

## Known limits of the fix

- A user with several LightDM sessions at once gets the first one listed:
  nothing links a LightDM session to a logind session to choose better.
- The screen locker's presence depends on cinnamon-session ignoring
  `NotShowIn=Unity` in `light-locker.desktop`. Not in scope here, and worth its
  own look.
