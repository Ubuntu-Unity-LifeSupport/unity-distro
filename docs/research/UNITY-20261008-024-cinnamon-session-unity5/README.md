# UNITY-20261008-024, UNITY-20261008-022: cinnamon-session +unity5 (logind session handling)

Agent A, target `target-desktop`.

## Problem

cinnamon-session +unity4 exports `SessionIsActive` and sends logind's idle
hint for "our" logind session. It found that session as the first of three
candidates that logind knew: the process's own session, `XDG_SESSION_ID`,
and the user's display session (`User.Display`). logind resolves any
user's session that way, and its display session can be a text session, so
a stale or inherited id could name a session that is not ours (for example
the user manager's session, class `manager`).

The systemd backend also mishandled the case of no session:
`csm_systemd_can_switch_user()` passed an unset variable to
`sd_seat_can_multi_session()` and `free()`, and
`csm_systemd_set_session_idle()` called `SetIdleHint` with no object path.
Nothing was logged when the session was removed.

## What is fixed

| package | version | change |
|---|---|---|
| cinnamon-session | 6.4.2-1+unity5 | Two new quilt patches after `Export-SessionIsActive-on-org.gnome.SessionManager`. |

- **UNITY-20261008-024**, `Take-only-this-user-s-open-graphical-session`:
  - every candidate must be owned by this user, be active or online (not
    closing), be of class `user` (the process's own session may also be a
    greeter) and be of type x11, wayland or mir;
  - the checks run in that order (sd-login), and a session that ends during
    them is rejected;
  - each rejection is logged at debug level;
  - with no candidate left, behaviour is as before: a warning, and the
    session counts as active.
- **UNITY-20261008-022**, `Handle-a-missing-or-removed-logind-session-in-the-systemd`:
  - switching users returns true without querying the seat
    (`sd_seat_can_multi_session()` is deprecated and always true since
    systemd 246, as gnome-session does since 49);
  - the idle hint is not sent without a session;
  - when logind removes our session, it is logged, and the session path and
    the proxy on it are dropped, so nothing more is sent to it.

## Build

Built with `scripts/build_sbuild.py` from the cinnamon-session package
branch `a/UNITY-20261008-024` (44343b4, on +unity4 `54ab973`), in chroot
snapshot T=20261008T083223Z. The orig tarball was regenerated from
pristine-tar. The manifest is in `build/`.

## Checks (on the target, `gate/target-test.txt`)

- **Discovery**, with the debug log of a fresh cinnamon-session for each
  value of `XDG_SESSION_ID`:
  - the user manager's session (class `manager`) is rejected;
  - a session no longer known to logind is rejected;
  - a text session (type `tty`) is rejected;
  - the display session is taken, from `XDG_SESSION_ID` or from
    `User.Display`;
  - `SessionIsActive` is true in every case.
- **Regression:**
  - `SessionIsActive` goes false and true across a VT switch;
  - an inserted medium is mounted;
  - after a relogin the old session's removal is logged, and the new
    session is found.

## Verification

- Target test before publication: PASS (`gate/target-test.txt`).
- Independent verification: PASS (the Verifier reviewed the patches, the
  build record and the runtime records; it did not reproduce on its own).
- Check on the target after publication: pending.

## Publication

- **Database backup:** `/home/claude/backups/UNITY-20261008-024-20261009T013135Z`.
  19 files, complete, equal to live; list sha256
  `2fa0932447459621a4b895bf7f17fa8a6ee66f00d0657303f1990e4a5f70e729`.
- **Repository:** 4 records added to `unity-resolute` (the source, 2 .deb
  and 1 .ddeb). The sha256 of every pool file matches the build manifest.
- **Snapshot:** `unity-resolute-20261008-024`, which is the live
  `unity-resolute-20261008-020` plus these 4 records
  (`gate/snapshot-diff.txt`).
- **Version safety:** SAFE (`gate/version-check.json`,
  `gate/version-safety.json`).
- **Peer notice:** agent B, ACK.

## Not changed / known limits

- The paths without any logind session (the switch-user query, the idle
  hint) were checked by review; the target always has a session.
- cinnamon-session's presence idle in the Unity session is
  UNITY-20261008-023, to be handled in unity-settings-daemon.
