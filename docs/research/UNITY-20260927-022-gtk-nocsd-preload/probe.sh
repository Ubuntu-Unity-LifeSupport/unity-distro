#!/bin/bash
# probe.sh LABEL - record where LD_PRELOAD ends up in the running X session.
# Run on the test desktop as the session user. Prints boot identity, package
# versions, the Xsession inputs, and LD_PRELOAD of the systemd user manager
# and of session processes.
label=$1
echo "== $label"
echo "date_utc: $(date -u +%FT%TZ)"
echo "boot_id: $(cat /proc/sys/kernel/random/boot_id)"
echo "uptime: $(uptime -p)"
echo "session_desktop: $(loginctl show-session "$(loginctl list-sessions --no-legend | awk '$3=="mike" && $0 !~ /tty/{print $1; exit}')" -p Desktop -p Type 2>/dev/null | tr '\n' ' ')"
for p in libgtk-nocsd0 libunity-gtk4-menu0 dbus-x11 dbus-user-session; do
  printf '%s: %s\n' "$p" "$(dpkg-query -W -f='${Version}' "$p" 2>/dev/null || echo not-installed)"
done
echo "51gtk-nocsd: $([ -e /etc/X11/Xsession.d/51gtk-nocsd ] && sha256sum /etc/X11/Xsession.d/51gtk-nocsd | cut -c1-16 || echo absent)"
echo "xsessionrc: $(grep -h LD_PRELOAD ~/.xsessionrc 2>/dev/null || echo none)"
echo "environment.d: $(grep -h LD_PRELOAD /usr/lib/environment.d/*.conf /etc/environment.d/*.conf 2>/dev/null | tr '\n' ' ')"
echo "user_manager: $(systemctl --user show-environment | grep '^LD_PRELOAD=' || echo 'LD_PRELOAD unset')"
for n in compiz xfwm4 xfce4-session unity-panel-service hud-service gnome-session-binary; do
  P=$(pidof -s "$n") || continue
  echo "$n: $(tr '\0' '\n' < /proc/$P/environ | grep '^LD_PRELOAD=' || echo 'LD_PRELOAD unset')"
done
