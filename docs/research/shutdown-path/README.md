# The shutdown path: known issues #2 and #6

Measured on target, boot 2026-09-23 20:44:50: snapshot Clean-updated-2026-09-23
plus libsystemd-dev, xdotool and light-locker 1.8.0-3ubuntu4+unity2, none of
which touch the session manager or Unity's shutdown code.

## #6, the double confirmation dialog - reproduced, mechanism proven

Session indicator -> "Выключение..." -> Unity's dialog ("До скорой встречи,
Mike") -> click "Выключить" -> a **second** dialog, "Выключить систему
сейчас?". Screenshot `2026-09-23-double-shutdown-dialog.png`. The machine does
not shut down; the second dialog waits.

The chain, each link measured:

1. **Unity 7 draws the first dialog itself** and, on confirmation, calls
   `org.gnome.SessionManager.Shutdown()`. Captured with `dbus-monitor`:

       method call sender=:1.85 -> destination=:1.49
         path=/org/gnome/SessionManager; interface=org.gnome.SessionManager; member=Shutdown

   `:1.85` is compiz, pid 2445; `:1.49` is `cinnamon-session-binary`, pid 1951.
   In the source, `GnomeManager::Shutdown()` in
   `UnityCore/GnomeSessionManager.cpp` sets `pending_action_ = SHUTDOWN` and
   makes that call.
2. **`org.gnome.SessionManager` is owned by cinnamon-session**, which
   implements the GNOME interface for compatibility.
3. **In cinnamon-session, `Shutdown()` means "show a dialog".**
   `csm_manager_shutdown()` calls `show_shutdown_dialog()` unconditionally;
   `logout-prompt` is not consulted on this path. The no-dialog variant is
   `RequestShutdown()` -> `request_shutdown()`.
4. **cinnamon-session asks the Cinnamon shell for the dialog, not Unity.**
   `show_end_session_dialog()` calls `ShowEndSessionDialog` on `org.Cinnamon`,
   `/org/Cinnamon`. Under Unity there is no Cinnamon shell, the call fails with
   `NAME_HAS_NO_OWNER`, and it falls back to its own GTK dialog -
   `cinnamon-session-quit`, the second dialog.
5. **Unity is ready for a handshake that never comes.** Unity implements
   `org.gnome.SessionManager.EndSessionDialog` - gnome-session's protocol for
   asking the shell to show the end-session dialog, where Unity, seeing its own
   `pending_action_`, would confirm silently. Verified registered on compiz's
   connection. cinnamon-session never calls it.

Under gnome-session, for which Unity 7 was written, that handshake is what
prevented a second dialog. Under cinnamon-session nothing replaces it.

**The release-note workaround** -
`gsettings set com.canonical.indicator.session suppress-logout-restart-shutdown true`
(the other four keys it lists are already their defaults) - suppresses
**Unity's** dialog and keeps cinnamon's. It removes the symptom by removing
Unity's own dialog.

A startup warning in the journal, `Can't register object
'org.gnome.SessionManager.EndSessionDialog' yet as we don't have a connection,
waiting for it...`, is transient: the object is registered moments later. Not
a cause.

## #2, the menu stops responding after cancelling - reproduced

The release note says "shutdown/logout menu not working after cancelling". On
2026-09-22 cancelling **Unity's** dialog did not reproduce it. The precondition
is cancelling the **second** dialog:

1. session indicator -> "Выключение..." -> Unity's dialog
2. confirm with "Выключить"
3. cancel cinnamon-session's "Выключить систему сейчас?" (Escape)
4. session indicator -> "Выключение..." again: **nothing opens.**

Persistent: two further attempts, zero dialogs each time.
`2026-09-23-shutdown-menu-stuck.png` shows the menu opening normally and no
dialog after choosing "Выключение...".

**Hypothesis, not yet proven:** #2 and #6 are one mechanism. After step 2 Unity
holds `pending_action_ = SHUTDOWN` and waits for the end-session handshake;
cinnamon-session's cancel in step 3 never reaches Unity, so Unity's state is
left pending and later requests are dropped. The code path in Unity that drops
them has not been found yet.

## Fix directions - not decided

- **Unity**, when the session manager is not gnome-session, calls
  `RequestShutdown()` / `RequestReboot()` after its own confirmation, since in
  cinnamon-session those skip the dialog. Keeps Unity's native dialog, which
  the workaround throws away.
- **cinnamon-session**, when the Cinnamon shell is absent, tries the shell's
  `org.gnome.SessionManager.EndSessionDialog` before falling back to GTK. That
  restores the handshake Unity was written for, and would likely fix #2 too.
- Which one is right is a question for the team as much as for us: it decides
  whether the fix belongs to Unity or to the Cinnamon layer Ubuntu Unity now
  depends on.
