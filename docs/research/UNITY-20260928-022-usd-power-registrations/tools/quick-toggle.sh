. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.power
P=$(pgrep -x unity-settings- | head -1)
cat > /tmp/adiag.gdb <<'G'
set pagination off
set breakpoint pending on
set confirm off
handle SIGCONT nostop noprint pass
dprintf gsd_power_manager_start,"START\n"
dprintf gsd_power_manager_stop,"STOP\n"
dprintf session_presence_proxy_ready_cb,"CB session_presence_proxy_ready\n"
dprintf power_keyboard_proxy_ready_cb,"CB power_keyboard_proxy_ready\n"
continue
G
sudo -n timeout 40 stdbuf -oL gdb -q -batch -p $P -x /tmp/adiag.gdb > /tmp/adiag.txt 2>&1 &
sleep 8
gsettings set $S active false; sleep 3
for i in 1 2 3; do gsettings set $S active true; gsettings set $S active false; sleep 3; done
gsettings set $S active true; sleep 5
wait
grep -E "^(START|STOP|CB)" /tmp/adiag.txt
echo "u-s-d alive: $(kill -0 $P && echo yes); crash: $(ls /var/crash | grep -c unity-settings)"
