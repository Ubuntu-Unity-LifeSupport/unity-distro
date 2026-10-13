#!/bin/sh
# UNITY-20260927-011 (from research/usd-color-logout-crash/runs/usd-gdb.sh):
# does the color plugin's session-proxy callback still run after the plugin
# was stopped? Stop the plugin (active=false), then make the session
# manager's properties change twice (take and drop an inhibitor). Under gdb
# with the package's debug symbols. Run as mike over ssh.
. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.color
P=$(pgrep -x unity-settings- | head -1)
echo "u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P"
cat > /tmp/usd.gdb <<'G'
set pagination off
set breakpoint pending on
dprintf gsd_color_manager_stop,"STOP manager=%p\n", manager
dprintf gcm_session_active_changed_cb,"CB manager=%p client=%p\n", manager, manager->priv->client
continue
G
sudo -n timeout 25 gdb -q -batch -p $P -x /tmp/usd.gdb > /tmp/usd-gdb.txt 2>&1 &
sleep 6; T=$(date +%T)
dbus-monitor --session "type='signal',interface='org.freedesktop.DBus.Properties',path='/org/gnome/SessionManager'" > /tmp/props.txt 2>&1 &
M=$!
gsettings set $S active false; sleep 2
timeout 4 gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager \
  --method org.gnome.SessionManager.Inhibit test 0 "usd color test" 4 >/dev/null
sleep 4; kill $M
wait
grep -E "^(STOP|CB)" /tmp/usd-gdb.txt
echo "session manager PropertiesChanged signals: $(grep -c InhibitedActions /tmp/props.txt)"
echo "criticals since $T: $(journalctl --since $T --no-pager | grep -c 'unity-settings-daemon.*\(CRITICAL\|assertion\)')"
journalctl --since $T --no-pager | grep 'unity-settings-daemon.*assertion' | cut -c40-170 | sort | uniq -c
gsettings set $S active true; sleep 3
echo "u-s-d pid now $(pgrep -x unity-settings- | head -1)"
