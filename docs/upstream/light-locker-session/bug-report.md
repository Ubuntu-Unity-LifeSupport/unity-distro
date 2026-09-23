# Comment for LP: #2038808

Not submitted. Needs May's agreement on this exact wording. Attach the two
patches from this directory.

---

This is reproducible on every login on Ubuntu Unity 26.04, with
light-locker 1.8.0-3ubuntu4 on a fully updated system. The cause is not
/proc and not hidepid.

Ubuntu Unity 26.04 runs cinnamon-session as the systemd user service
unity-session.service, and light-locker is started as its child. It therefore
lives in user@UID.service rather than in the logind session scope.
init_session_id() asks logind GetSessionByPID for its own PID, logind answers
"PID ... does not belong to any known session", and g_error() aborts. The
XDG_SESSION_ID fallback already in this package does not help: it only covers
the second lookup, and the variable is not in the user manager's environment
anyway.

With that fixed, light-locker gets one step further and aborts again in
query_seat_path(), on "XDG_SESSION_PATH not set. Is LightDM running?", for the
same reason: LightDM sets that variable for the session it starts, and a
process started by a user service never inherits it.

The two attached patches handle both. The first falls back to the user's
display session from logind (sd_uid_get_display, then GetSession) when the PID
lookup fails. The second reads LightDM's Sessions over D-Bus when
XDG_SESSION_PATH is missing and takes the one belonging to the user. Existing
behaviour inside a session scope is unchanged, and the original errors remain
for the case where neither logind nor LightDM can answer.

Tested on 26.04 in a clean chroot build and on a desktop: light-locker stays
up after login, owns org.freedesktop.ScreenSaver, and light-locker-command -l
switches to the greeter in unlock mode, and unlocking with the password
returns to the session - checked by hand on the desktop, with LightDM logging
the successful authentication and the unlock of the logind session.

Upstream PR #153 (the-cavalry/light-locker) aims at the same problem but does
not fix this case: it does not handle XDG_SESSION_PATH, so it still aborts on
26.04, and it passes a logind object path to sd_session_is_active(), which
returns -EINVAL and silently disables the check that refuses to lock an
inactive session. Upstream has been inactive since 2020, so these are proposed
for the Ubuntu package.

Part of this investigation and the patches were prepared with AI assistance;
the reproduction, builds and desktop testing were run and checked by hand.
