#!/bin/sh
# UNITY-20260928-022: D-Bus behaviour of the power plugin, running and
# stopped, and the logind inhibitors around quick on/off toggles.
# Run as mike over ssh. Prints one line per check.
. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.power
P=$(pgrep -x unity-settings- | head -1)
echo "u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P"
T=$(date +%T)
get() { t0=$(date +%s.%N); r=$(timeout 40 gdbus call --session --dest org.gnome.SettingsDaemon.Power --object-path /org/gnome/SettingsDaemon/Power --method org.freedesktop.DBus.Properties.Get org.gnome.SettingsDaemon.Power "$1" 2>&1 | head -1 | cut -c1-110); echo "  Get $1 ($(echo "$(date +%s.%N) - $t0" | bc | cut -c1-5) s): $r"; }
meth() { t0=$(date +%s.%N); r=$(timeout 40 gdbus call --session --dest org.gnome.SettingsDaemon.Power --object-path /org/gnome/SettingsDaemon/Power --method org.gnome.SettingsDaemon.Power.Screen.GetPercentage 2>&1 | head -1 | cut -c1-110); echo "  Screen.GetPercentage ($(echo "$(date +%s.%N) - $t0" | bc | cut -c1-5) s): $r"; }
alive() { echo "  u-s-d pid $P alive: $(kill -0 $P 2>/dev/null && echo yes || echo no)"; }
inh() { Q=$(pgrep -x unity-settings- | head -1); echo "  u-s-d (pid $Q) logind inhibitors: $(systemd-inhibit --list --no-legend | awk -v p=$Q '$4==p' | awk '{$1=$2=$3=$4=""; print}' | sed 's/^ *//' | tr '\n' ';' | cut -c1-200)"; }
echo "== plugin running"; get Percentage; get Icon; meth; alive; inh
gsettings set $S active false; sleep 3
echo "== plugin stopped"; get Percentage; get Icon; meth; alive
echo "== quick on/off x3, then on"
for i in 1 2 3; do gsettings set $S active true; gsettings set $S active false; sleep 3; done
inh
gsettings set $S active true; sleep 5
echo "== plugin running again"; get Icon; meth; alive; inh
echo "journal since $T: $(journalctl --since $T --no-pager | grep -cE 'unity-settings.*(ERROR|assert|dumped|segfault)')"
