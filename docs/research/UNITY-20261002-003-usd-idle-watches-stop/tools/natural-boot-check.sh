#!/bin/sh
# UNITY-20261002-003 re-check on a clean snapshot: state after one natural boot
# into the users' session (run as mike on target).
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
echo "natural boot check $(date -u +%FT%TZ): uptime $(uptime)"
echo " boot started: $(uptime -s)"
printf ' versions: '
dpkg-query -W -f '${Package} ${Version}; ' cinnamon-session unity-settings-daemon unity-settings-daemon-schemas libunity-settings-daemon1 2>/dev/null; echo
grep -q gnome.is_vm /proc/cmdline && echo " cmdline gnome.is_vm: PRESENT" || echo " cmdline gnome.is_vm: absent"
pid=$(pgrep -x -u "$(id -u)" unity-settings- | head -1)
[ -z "$pid" ] && pid=$(pgrep -u "$(id -u)" -f '[u]nity-settings-daemon' | head -1)
echo " u-s-d pid: ${pid:-none}"
[ -n "$pid" ] && echo " u-s-d replaced maps: $(grep -c '(deleted)' /proc/$pid/maps)"
echo " Power owner: $(gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetNameOwner org.gnome.SettingsDaemon.Power 2>&1)"
for u in unity-settings-daemon.service; do
  echo " $u: $(systemctl --user show -p ActiveState -p NRestarts $u 2>&1 | tr '\n' ' ')"
done
echo " crash files: $(ls /var/crash 2>/dev/null | wc -l) $(ls /var/crash 2>/dev/null | tr '\n' ' ')"
echo " dpkg -V u-s-d: $(dpkg -V unity-settings-daemon unity-settings-daemon-schemas libunity-settings-daemon1 2>&1 | wc -l) lines"
echo " sleep-inactive-ac-timeout: $(gsettings get com.canonical.unity.settings-daemon.plugins.power sleep-inactive-ac-timeout), battery: $(gsettings get com.canonical.unity.settings-daemon.plugins.power sleep-inactive-battery-timeout)"
echo " installed debs from the repository (apt cache):"
for f in /var/cache/apt/archives/unity-settings-daemon_*unity11*.deb /var/cache/apt/archives/unity-settings-daemon-schemas_*unity11*.deb /var/cache/apt/archives/libunity-settings-daemon1_*unity11*.deb; do
  [ -f "$f" ] && echo "  $(sha256sum "$f")"
done
echo " ~/.dirty: $(ls ~/.dirty 2>&1)"
