#!/bin/sh
# UNITY-20260927-011 (from research/usd-color-logout-crash/runs/usd-color-restart.sh):
# switch the color plugin off and on under gdb - does it start again
# (connect to colord) or stay dead? Run as mike over ssh.
. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.color
P=$(pgrep -x unity-settings- | head -1)
echo "u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P"
cat > /tmp/usdr.gdb <<'G'
set pagination off
set breakpoint pending on
dprintf gsd_color_manager_stop,"STOP\n"
dprintf gsd_color_manager_start,"START\n"
dprintf gcm_session_client_connect_cb,"COLORD-CONNECTED\n"
continue
G
sudo -n timeout 20 gdb -q -batch -p $P -x /tmp/usdr.gdb > /tmp/usdr.txt 2>&1 &
sleep 6; T=$(date +%T)
gsettings set $S active false; sleep 3
gsettings set $S active true; sleep 6
wait
grep -E "^(STOP|START|COLORD-CONNECTED)" /tmp/usdr.txt
echo "criticals since $T: $(journalctl --since $T --no-pager | grep -c 'unity-settings-daemon.*\(CRITICAL\|assertion\)')"
journalctl --since $T --no-pager | grep 'unity-settings-daemon.*assertion' | cut -c40-170 | sort | uniq -c
echo "colord devices for this display: $(gdbus call --system --dest org.freedesktop.ColorManager --object-path /org/freedesktop/ColorManager --method org.freedesktop.ColorManager.GetDevices 2>/dev/null | grep -o xrandr | wc -l)"
echo "u-s-d pid now $(pgrep -x unity-settings- | head -1); crash files: $(ls /var/crash | tr '\n' ' ')"
