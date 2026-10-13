#!/bin/bash
# session-check.sh TAG - on target2 (as mike over ssh), after a cold boot with autologin: what a Unity session with
# the given preload stack does to PyGObject programs.
#   - the preload: LD_PRELOAD of the user manager and of compiz, the libraries in compiz's maps, the opt-out file
#   - the Python session components started from /etc/xdg/autostart: running or not
#   - GObject Introspection errors in this boot's user journal and in ~/.xsession-errors
#   - four Python programs started through the user manager (systemd-run --user, as the launcher starts them): meld
#     (GTK3), gnome-tweaks (GTK4 + libadwaita), and a minimal GTK3 and GTK4 window from apps.py; each one alive or not
#     after 8 s, its window, and the last lines of its unit's journal
set -u
tag=$1; B=~/b1313
cp=$(pgrep -x compiz | head -1)
export $(tr '\0' '\n' < /proc/${cp:?no compiz}/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR)=')
echo "== $tag at $(date -u +%FT%TZ), boot $(uptime -s); $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}, ' libunity-gtk4-menu0)$(dpkg-query -W -f='libgtk-nocsd0 ${Version}' libgtk-nocsd0)"
echo "-- preload"
echo "  opt-out file: $(ls -l ~/.config/environment.d/50-gtk-nocsd.conf 2>&1)"
systemctl --user show-environment | grep '^LD_PRELOAD=' | sed 's/^/  user manager: /'
echo "  compiz: $(tr '\0' '\n' < /proc/$cp/environ | grep '^LD_PRELOAD=' || echo 'LD_PRELOAD unset')"
echo "  compiz maps: $(grep -oE 'lib(gtk-nocsd|unity-gtk4-menu)\.so\.0' /proc/$cp/maps | sort -u | xargs)"
echo "-- Python session components (autostart)"
for f in /etc/xdg/autostart/*.desktop; do
  e=$(sed -n 's/^Exec=//p' "$f" | head -1 | awk '{print $1}'); p=$(command -v "$e" 2>/dev/null) || continue
  head -1 "$p" 2>/dev/null | grep -q python || continue
  # a python program runs as python3, so look for its path in the cmdlines of this user's python3 processes
  pids=$(ps -u "$(id -u)" -o pid=,args= | awk -v p="$p" '$2 ~ /python3$/ && $3 == p {print $1}' | xargs)
  shown=$(grep -hE '^(OnlyShowIn|NotShowIn|X-GNOME-AutoRestart|AutostartCondition|X-GNOME-Autostart-enabled)=' "$f" | xargs)
  echo "  $(basename "$f") -> $p: $([ -n "$pids" ] && echo "running pid $pids" || echo "not running") [$shown]"
done
echo "-- GObject Introspection errors of this boot"
echo "  user journal: $(journalctl --user -b --no-pager -q | grep -cE 'AssertionError|g_type != TYPE_NONE|gi/overrides') lines; ~/.xsession-errors: $(grep -cE 'AssertionError|gi/overrides' ~/.xsession-errors 2>/dev/null) lines"
journalctl --user -b --no-pager -q -o cat | grep -B3 -E 'AssertionError' | head -12 | sed 's/^/    /'
echo "-- Python programs through the user manager"
for a in meld gnome-tweaks "python3 $B/apps.py 3" "python3 $B/apps.py 4"; do
  u=b1313-$(echo "$a" | tr -c 'a-z0-9\n' '-' | cut -c1-30)
  systemctl --user reset-failed "$u" 2>/dev/null
  systemd-run --user --quiet --unit="$u" $a; sleep 8
  st=$(systemctl --user show "$u" -p ActiveState -p Result -p ExecMainStatus --value | xargs)
  pid=$(systemctl --user show "$u" -p MainPID --value)
  w=$([ "$pid" -gt 0 ] && xdotool search --onlyvisible --pid "$pid" 2>/dev/null | head -1)
  echo "  $a: unit $st, main pid $pid, window ${w:-none}${w:+ $(xprop -id "$w" _GTK_MENUBAR_OBJECT_PATH 2>&1 | cut -c1-70)}"
  journalctl --user -b --no-pager -q -o cat -u "$u" | grep -vE 'xdg-desktop-portal|portal.Inhibit' | tail -3 | sed 's/^/      /'
  systemctl --user stop "$u" 2>/dev/null; systemctl --user reset-failed "$u" 2>/dev/null
done
true
