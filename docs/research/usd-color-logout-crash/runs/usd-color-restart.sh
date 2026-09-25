#!/bin/sh
# Switch u-s-d's color plugin off and on under gdb: does it start again
# (connect to colord) or stay dead?
. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.color
P=$(pgrep -f "[u]nity-settings-daemon$" | head -1)
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
sleep 5; T=$(date +%T)
gsettings set $S active false; sleep 3
gsettings set $S active true; sleep 6
wait
grep -E "^(STOP|START|COLORD-CONNECTED)" /tmp/usdr.txt
echo "criticals: $(journalctl --since $T --no-pager | grep -c 'unity-settings-daemon.*CRITICAL\|unity-settings-daemon.*assertion')"
journalctl --since $T --no-pager | grep 'unity-settings-daemon.*assertion' | cut -c40-160 | sort | uniq -c
echo "u-s-d pid now $(pgrep -f '[u]nity-settings-daemon$' | head -1); crash files: $(ls /var/crash | tr '\n' ' ')"
