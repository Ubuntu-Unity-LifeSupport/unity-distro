#!/bin/bash
# UNITY-20260928-022: stop() before on_bus_gotten. Runs unity-settings-daemon
# under gdb in the live session instead of its systemd unit. At
# gsd_power_manager_start (register_manager_dbus already queued the one
# g_bus_get() of the process from gsd_power_manager_new) gdb lets start()
# finish, then calls gsd_power_manager_stop() before the main loop can deliver
# the bus result -
# what happens when the plugin is stopped while the bus request is pending.
# Then the plugin is cycled the normal way (gsettings active false -> true)
# and the script reports whether org.gnome.SettingsDaemon.Power has an owner
# and whether a Power call is answered.
# usage: stop-before-bus.sh [nostop]   (nostop: same run without the stop call)
# UNITY-20261002-002 (Design Challenger D6b): also a method call, Screen.GetPercentage,
# which must get a value or the -022 error, never NoReply/ServiceUnknown.
. ~/envt.sh
MODE=${1:-stop}
# +unity7 and older have no bus_cancellable field: do not print it there
V=$(dpkg-query -W -f '${Version}' unity-settings-daemon)
F=", ((GsdPowerManager *) manager_object)->priv->bus_cancellable"; FMT=' bus_cancellable=%p'
case $V in *+unity9|*+unity1[0-9]) ;; *) F=; FMT=;; esac
S=com.canonical.unity.settings-daemon.plugins.power
C=$(pgrep -x compiz)
eval "export $(tr '\0' '\n' < /proc/$C/environ | grep -E '^(DISPLAY|XAUTHORITY|XDG_CURRENT_DESKTOP|XDG_SESSION_TYPE|XDG_SESSION_ID|DESKTOP_SESSION|GDMSESSION)=' | tr '\n' ' ')"
owner() { gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
  --method org.freedesktop.DBus.GetNameOwner org.gnome.SettingsDaemon.Power 2>&1 | cut -c1-70; }
call() { gdbus call --session --dest org.gnome.SettingsDaemon.Power --object-path /org/gnome/SettingsDaemon/Power \
  --method org.freedesktop.DBus.Properties.Get org.gnome.SettingsDaemon.Power Icon 2>&1 | cut -c1-90; }
echo "u-s-d $(dpkg-query -W -f '${Version}' unity-settings-daemon), mode $MODE, $(date +%T)"
gsettings set $S active true
systemctl --user stop unity-settings-daemon.service 'app-unity\x2dsettings\x2ddaemon@autostart.service' 2>/dev/null
sleep 2
G=/tmp/sbb.gdb
{
  echo 'set pagination off'; echo 'set confirm off'; echo 'set breakpoint pending on'
  echo 'handle SIGPIPE nostop noprint pass'; echo 'handle SIGTERM nostop noprint pass'
  echo 'break gsd_power_manager_start'
  echo 'run'
  echo 'finish'
  echo "printf \"START-RETURNED$FMT\\n\"$F"
  if [ "$MODE" = stop ]; then
    echo 'call (void) gsd_power_manager_stop (manager_object)'
    echo "printf \"STOP-CALLED$FMT\\n\"$F"
  fi
  echo 'delete'
  echo 'break on_bus_gotten'
  echo 'commands'; echo 'silent'; echo 'printf "ON-BUS-GOTTEN\n"'; echo 'continue'; echo 'end'
  echo 'continue'
} > $G
setsid gdb -q -batch -x $G /usr/lib/unity-settings-daemon/unity-settings-daemon > /tmp/sbb-gdb.txt 2>&1 < /dev/null &
GP=$!
sleep 25
echo "after start: owner $(owner)"
gsettings set $S active false; sleep 3; gsettings set $S active true; sleep 6
echo "after plugin off/on: owner $(owner)"
echo "Power Get Icon: $(call)"
echo "Power Screen.GetPercentage: $(gdbus call --session --dest org.gnome.SettingsDaemon.Power --object-path /org/gnome/SettingsDaemon/Power --method org.gnome.SettingsDaemon.Power.Screen.GetPercentage 2>&1 | cut -c1-110)"
grep -E "START-RETURNED|STOP-CALLED|ON-BUS-GOTTEN|SIGSEGV|SIGABRT|signal SIG" /tmp/sbb-gdb.txt
pkill -TERM -x unity-settings- 2>/dev/null; sleep 2; kill $GP 2>/dev/null; wait $GP 2>/dev/null
systemctl --user start unity-settings-daemon.service; sleep 6
echo "u-s-d back under systemd: owner $(owner)"
