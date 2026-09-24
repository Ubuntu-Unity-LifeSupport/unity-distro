#!/bin/sh
. ~/envt.sh
P=$(pgrep -f "[u]nity-settings-daemon$" | head -1)
cat > /tmp/usd.gdb <<'G'
set pagination off
set breakpoint pending on
dprintf gsd_color_manager_stop,"STOP manager=%p\n", manager
dprintf gcm_session_active_changed_cb,"CB manager=%p client=%p\n", manager, manager->priv->client
continue
G
sudo -n timeout 25 gdb -q -batch -p $P -x /tmp/usd.gdb > /tmp/usd-gdb.txt 2>&1 &
sleep 5
dbus-monitor --session "type='signal',interface='org.freedesktop.DBus.Properties',path='/org/gnome/SessionManager'" > /tmp/props.txt 2>&1 &
M=$!
gsettings set com.canonical.unity.settings-daemon.plugins.color active false; sleep 2
timeout 4 gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager --method org.gnome.SessionManager.Inhibit test 0 "usd color test" 4
sleep 4; kill $M
wait
grep -E "STOP|CB|signal" /tmp/usd-gdb.txt /tmp/props.txt | head; grep -c InhibitedActions /tmp/props.txt
gsettings set com.canonical.unity.settings-daemon.plugins.color active true
