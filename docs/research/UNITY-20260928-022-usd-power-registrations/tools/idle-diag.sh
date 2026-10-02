. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.power
P=$(pgrep -x unity-settings- | head -1)
cat > /tmp/idiag.gdb <<'G'
set pagination off
set breakpoint pending on
set confirm off
handle SIGCONT nostop noprint pass
dprintf idle_configure,"idle_configure\n"
dprintf gsd_idle_monitor_add_idle_watch,"add_idle_watch %u ms\n", interval_msec
dprintf gsd_idle_monitor_add_user_active_watch,"add_user_active_watch\n"
dprintf idle_triggered_idle_cb,"idle_triggered watch=%u\n", watch_id
dprintf idle_became_active_cb,"became_active\n"
dprintf idle_set_mode,"idle_set_mode %d\n", mode
continue
G
sudo -n timeout 70 stdbuf -oL gdb -q -batch -p $P -x /tmp/idiag.gdb > /tmp/idiag.txt 2>&1 &
sleep 8
gsettings set $S sleep-inactive-ac-type "'blank'"; gsettings set $S sleep-inactive-ac-timeout 20
echo "idle counter before wait: $(xprintidle 2>/dev/null || echo n/a)"
sleep 35
xdotool mousemove_relative 30 30; sleep 5
wait
grep -vE "^\[|^Using|^warning|^$|syscall_cancel|^0x" /tmp/idiag.txt | head -30
gsettings reset $S sleep-inactive-ac-type; gsettings reset $S sleep-inactive-ac-timeout
