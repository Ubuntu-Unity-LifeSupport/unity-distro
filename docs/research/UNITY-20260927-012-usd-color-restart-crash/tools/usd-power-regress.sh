#!/bin/sh
# UNITY-20260927-012: the power plugin still hears the shared proxies while
# it runs (the fix only disconnects at stop): count its session and
# screensaver handlers under gdb for (1) an inhibitor taken and dropped,
# (2) a screen lock and unlock, (3) the plugin switched off - then the same
# inhibitor, (4) switched on again - the same inhibitor (handlers attached
# again, once). Run as mike over ssh.
. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.power
P=$(pgrep -x unity-settings- | head -1)
echo "u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P"
cat > /tmp/reg.gdb <<'G'
set pagination off
set breakpoint pending on
set confirm off
handle SIGCONT nostop noprint pass
dprintf engine_session_properties_changed_cb,"POWER-SESSION-CB\n"
dprintf screensaver_signal_cb,"POWER-SCREENSAVER-CB %s\n", signal_name
dprintf idle_configure,"IDLE-CONFIGURE\n"
continue
G
sudo -n timeout 120 stdbuf -oL -eL gdb -q -batch -p $P -x /tmp/reg.gdb > /tmp/reg.txt 2>&1 &
sleep 8
mark() { sleep 2; echo "== $1: $(grep -cE 'POWER-SESSION' /tmp/reg.txt) session / $(grep -cE 'POWER-SCREENSAVER' /tmp/reg.txt) screensaver callbacks so far"; }
inhibit() { timeout 4 gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager \
  --method org.gnome.SessionManager.Inhibit test 0 "u012 regress" 8 >/dev/null; sleep 6; }
mark start
inhibit; mark "1 inhibitor"
SID=$(loginctl list-sessions --no-legend | awk '$3=="mike" && $4=="seat0"{print $1}')
sudo -n loginctl lock-session $SID; sleep 5; sudo -n loginctl unlock-session $SID; sleep 5; mark "2 lock+unlock"
gsettings set $S active false; sleep 3; inhibit; mark "3 plugin off + inhibitor"
gsettings set $S active true; sleep 5; inhibit; mark "4 plugin on + inhibitor"
sudo -n pkill -x gdb; wait
echo "--- callbacks in order"
grep -E "^(POWER-|IDLE-)" /tmp/reg.txt | uniq -c
