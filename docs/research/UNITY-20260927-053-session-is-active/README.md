# UNITY-20260927-053: cinnamon-session exports SessionIsActive; automount works in the Unity session

Agent A, target `target-desktop`.

## Problem

In the Ubuntu Unity 26.04 session, cinnamon-session is the session manager
and owns `org.gnome.SessionManager`. Unlike gnome-session (since 3.7.2), it
did not export the property `SessionIsActive`: whether the user's logind
session is the active one on its seat. unity-settings-daemon's plugins read
that property, and a missing property reads as "inactive":

- the automount helper never mounted a medium inserted into a running
  session, and never offered autorun (a medium present at login was
  mounted, by a separate path);
- the color plugin logged `assertion 'active_v != NULL' failed` on every
  property change;
- the power plugin never enabled its idle handling.

cinnamon-session also failed to find its own logind session when started
as a systemd user service (`unity-session.service`), and logged "Could not
get session id for session" at every login.

## What is fixed

| package | version | change |
|---|---|---|
| cinnamon-session | 6.4.2-1+unity4 | New quilt patch `Export-SessionIsActive-on-org.gnome.SessionManager`. `CsmSystem` gets an `active` property, default TRUE (a session that cannot be found must not look inactive). The logind backend follows `Session.Active` of its session through a D-Bus proxy. The session is found by the process's own session, `XDG_SESSION_ID`, or logind's `User.Display`, each verified with `GetSession`. The manager binds the property to the exported `org.gnome.SessionManager` interface right after the export. |

## Who reads SessionIsActive (installed set, Unity session)

| consumer | package | effect of the property |
|---|---|---|
| automount helper | unity-settings-daemon | mounts a medium inserted into the active, unlocked session, and offers autorun |
| power plugin | unity-settings-daemon | idle handling runs. On AC there is no idle suspend: the schema override from +unity11 sets `sleep-inactive-ac-timeout=0`. |
| color plugin | unity-settings-daemon | the assertion is gone |
| indicator-session, xdg-desktop-portal-gtk | (bundled interface description only) | none |

## Build

Built with `scripts/build_sbuild.py` from the cinnamon-session package branch
`a/UNITY-20260927-053` (54ab973, on +unity3 `fadd8c6`), in chroot snapshot
T=20261008T083223Z. The orig tarball was regenerated from pristine-tar. The
manifest is in `build/`.

## Checks (properties measured on the target)

The target is the published stack (unity-settings-daemon +unity12, unity
+unity13, light-locker +unity3) plus cinnamon-session +unity4. Target
record: `gate/target-test.txt`.

- **The property:**
  - `SessionIsActive` is true in the session;
  - on a switch to another VT and back it goes false and then true, and
    `PropertiesChanged` is sent each time (5 cycles);
  - the journal has no "Could not get session id" and no color assertion,
    and that still holds after a logout and a new login in the same boot.
- **Mounting in an unlocked session:** a medium inserted is mounted, also
  in a new session after a logout.
- **Mounting while the session is locked:**
  - a medium inserted is not mounted;
  - after the user logs in again, that medium stays unmounted;
  - a medium inserted after the login is mounted.
- **Autorun:**
  - off by default (`autorun-never=true`), so no dialog appears;
  - with autorun enabled by the user, the autorun dialog appears for an
    inserted medium (a run outside the published configuration).
- **Idle:**
  - logind's `IdleAction` is `ignore`;
  - the power schema has `sleep-inactive-ac-timeout=0`, so there is no
    suspend on AC;
  - on a virtual machine the power plugin's idle handling is off by
    design, so dim and blank can only be observed on real hardware;
  - cinnamon-session's own presence never becomes idle in the Unity
    session, so it never sets logind's `IdleHint`. Its idle monitor
    (libcinnamon-desktop) asks `org.cinnamon.Muffin.IdleMonitor`, which only
    Cinnamon's window manager provides; in the Unity session that name has
    no owner (unity-settings-daemon provides `org.gnome.Mutter.IdleMonitor`
    instead). Measured with `idle-delay` 30 s after a cold boot: the X
    server's idle time passed 150 s, presence stayed "available",
    `IdleHint` stayed "no". The same holds with +unity3; this version does
    not change it.

## Release note

With this version the following work on real hardware for the first time
in the Unity session:

- unity-settings-daemon's power idle handling: dim, blank, and suspend on
  battery (the schema defaults; no suspend on AC);
- the screen blanks when the session locks;
- automount of inserted media;
- autorun, if the user has enabled it (off by default).

## Verification

- Target test before publication: PASS, record in `gate/target-test.txt`.
- Independent verification: pending.
- Check on the target after publication: pending.

## Not changed / known limits

- The automount helper itself is unchanged; its lock-state check is that
  of unity-settings-daemon +unity12 (UNITY-20261002-012).
- A killed automount helper is not restarted by cinnamon-session
  (UNITY-20261002-010).
- Which screen locker the Unity session keeps is UNITY-20261008-006.
- cinnamon-session's presence never becomes idle in the Unity session,
  because `org.cinnamon.Muffin.IdleMonitor` is missing there; unchanged by
  this version (UNITY-20261008-023).
