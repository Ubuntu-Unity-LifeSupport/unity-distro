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
echo "-- Python programs through the user manager (12 s each; the session components are started again by hand)"
n=0
for a in meld gnome-tweaks "python3 $B/apps.py 3" "python3 $B/apps.py 4" unity-indicator-appearance onboard orca \
         uwidgets-runner update-manager software-properties-gtk /usr/share/apport/apport-gtk; do
  n=$((n+1)); u=b1313-$tag-$n
  systemd-run --user --quiet --unit="$u" $a; sleep 12
  st=$(systemctl --user show "$u" -p ActiveState -p Result -p ExecMainStatus --value | xargs)
  pid=$(systemctl --user show "$u" -p MainPID --value)
  w=$([ "$pid" -gt 0 ] && xdotool search --onlyvisible --pid "$pid" 2>/dev/null | head -1)
  tb=$(journalctl --user -b --no-pager -q -o cat -u "$u" | grep -cE 'AssertionError|Traceback')
  echo "  $a: unit $st, main pid $pid, window ${w:-none}${w:+ $(xprop -id "$w" _GTK_MENUBAR_OBJECT_PATH 2>&1 | cut -c1-60)}; Traceback/AssertionError lines $tb"
  journalctl --user -b --no-pager -q -o cat -u "$u" | grep -vE 'xdg-desktop-portal|portal.Inhibit|^Started |^Stopp|Consumed' | tail -2 | cut -c1-150 | sed 's/^/      /'
  systemctl --user stop "$u" 2>/dev/null; systemctl --user reset-failed "$u" 2>/dev/null
done
echo "-- GIO modules in a PyGObject process (the dconf backend is a GIO module); the session's LD_PRELOAD, from compiz"
export LD_PRELOAD="$(tr '\0' '\n' < /proc/$cp/environ | sed -n 's/^LD_PRELOAD=//p')"
echo "  LD_PRELOAD=$LD_PRELOAD"
python3 -c 'from gi.repository import Gio; b = Gio.SettingsBackend.get_default(); print("  backend:", type(b).__name__, "GSETTINGS_BACKEND:", __import__("os").environ.get("GSETTINGS_BACKEND"))' 2>&1 | tail -1
python3 -c 'from gi.repository import Gio; s = Gio.Settings.new("org.gnome.desktop.interface"); v = s.get_boolean("clock-show-seconds"); s.set_boolean("clock-show-seconds", not v); Gio.Settings.sync(); print("  write:", v, "->", not v)' 2>&1 | tail -1
echo "  read back from dconf: $(dconf read /org/gnome/desktop/interface/clock-show-seconds)"
python3 -c 'from gi.repository import Gio; s = Gio.Settings.new("org.gnome.desktop.interface"); s.reset("clock-show-seconds"); Gio.Settings.sync()' 2>&1 | tail -1
echo "-- maps of non-GTK processes with the session's LD_PRELOAD"
echo "  cat: ours mapped $(cat /proc/self/maps | grep -c libunity-gtk4-menu), libgmodule/libgtk-4 mapped $(cat /proc/self/maps | grep -cE 'libgmodule|libgtk-4'); python3 without gi: libgmodule/libgtk-4 mapped $(python3 -c 'print(sum(1 for l in open("/proc/self/maps") if "libgmodule" in l or "libgtk-4" in l))')"
unset LD_PRELOAD
true
