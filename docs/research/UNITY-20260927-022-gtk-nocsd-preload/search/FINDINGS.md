# UNITY-20260927-022 existing-fix / issue search (2026-09-27)

Delegated to an isolated search subagent; summary checked by agent B.

1. `/etc/X11/Xsession.d/95dbus_update-activation-env` is shipped by
   **dbus-x11 1.16.2-2ubuntu4** (resolute/main). It unsets XDG_SEAT,
   XDG_SEAT_PATH, XDG_SESSION_ID, XDG_SESSION_PATH, XDG_VTNR and runs
   `dbus-update-activation-environment --verbose --systemd --all`. The tool
   has no variable filter (dbus-1.16.2 and main,
   https://gitlab.freedesktop.org/dbus/dbus/-/blob/dbus-1.16.2/tools/dbus-update-activation-environment.c);
   systemd's `sanitize_environment()` does not drop LD_PRELOAD.
2. systemd v259 (resolute 259.5-0ubuntu3.4), `manager_get_effective_environment()`
   = `strv_env_merge(transient_environment, client_environment)`: an imported
   (client) value replaces the environment.d value for the same key, by design;
   the two are never concatenated (https://github.com/systemd/systemd/blob/v259/src/core/manager.c).
   systemctl(1) documents two separate blocks that are "combined";
   import-environment without names is deprecated. Related open issue:
   https://github.com/systemd/systemd/issues/41357.
3. Debian gtk-nocsd (https://salsa.debian.org/ubports-team/gtk-nocsd): only
   `master` 5e3e22334857, newest tag debian/4.8-1, no Xsession script; ships
   `50-gtk-nocsd.conf` = `LD_PRELOAD=libgtk-nocsd.so.0${LD_PRELOAD:+:$LD_PRELOAD}`.
   Ubuntu stonking: 4.8-1, no delta. Upstream
   https://codeberg.org/MorsMortium/GTK-NoCSD at e817d809bd97: no Xsession
   script, no environment.d merge. Old gtk3-nocsd
   (https://sources.debian.org/src/gtk3-nocsd/3-2/debian/extra/):
   `51gtk3-nocsd-detect` prepended `libgtk3-nocsd.so.0${LD_PRELOAD:+:$LD_PRELOAD}`
   without systemd awareness; `70gtk3-nocsd-propagate-LD_PRELOAD` set
   `STARTUP="env LD_PRELOAD=$LD_PRELOAD $STARTUP"`.
4. Issues: no report of this exact overwrite. Related: Debian #1131504
   (environment.d does not reach non-systemd X sessions; an Xsession script
   must check for a duplicate), systemd #41357, LP #1644323 and LP #1843997
   (the same problem for GTK_MODULES), LP #1861363.
   Searched: Debian BTS (src gtk-nocsd, gtk3-nocsd, archive=both), Launchpad
   searchTasks (gtk-nocsd, gtk3-nocsd, dbus, systemd, ubuntu-wide queries on
   LD_PRELOAD / environment.d / dbus-update-activation-environment /
   xsessionrc), Codeberg GTK-NoCSD issues, GitHub (systemd/systemd and
   global). Not searched: freedesktop GitLab dbus issues; Debian codesearch
   returned 403.
5. Convention: no shared mechanism for several packages contributing to
   LD_PRELOAD in X sessions; each prepends its own entry. The GTK_MODULES
   precedent was fixed per package (e.g. `90atk-adaptor` re-adds
   `gail:atk-bridge` in Xsession and imports GTK_MODULES itself).

existing_fix_result candidate: NOT_FIXED. issue_search_result: NOT_FOUND
(exact issue), with the related reports above.
