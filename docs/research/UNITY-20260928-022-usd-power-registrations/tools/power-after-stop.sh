#!/bin/sh
# UNITY-20260928-022: what reaches the power manager after gsd_power_manager_stop().
# MODE=stopped: the plugin is switched off (active=false) - stopped, not finalized.
# MODE=finalized: gdb makes u-s-d run gnome_settings_manager_stop() (every plugin
#   finalized) and leaves its main loop running (needs the perturb drop-in).
# Then: (1) a D-Bus call to org.gnome.SettingsDaemon.Power, timed; (2) 30 s
# without input with a 20 s AC sleep watch of type 'blank'; (3) pointer moved.
# Run as mike over ssh. Usage: power-after-stop.sh stopped|finalized
. ~/envt.sh
MODE=${1:?stopped|finalized}
S=com.canonical.unity.settings-daemon.plugins.power
P=$(pgrep -x unity-settings- | head -1)
echo "u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P mode $MODE $(sudo cat /proc/$P/environ | tr '\0' '\n' | grep ^GLIBC_TUNABLES=)"
OLDT=$(gsettings get $S sleep-inactive-ac-type); OLDS=$(gsettings get $S sleep-inactive-ac-timeout)
gsettings set $S sleep-inactive-ac-type "'blank'"; gsettings set $S sleep-inactive-ac-timeout 20; sleep 2
call() { t0=$(date +%s.%N); r=$(timeout 40 gdbus call --session --dest org.gnome.SettingsDaemon.Power --object-path /org/gnome/SettingsDaemon/Power --method org.gnome.SettingsDaemon.Power.Screen.GetPercentage 2>&1 | head -1 | cut -c1-110); echo "  D-Bus Screen.GetPercentage after $(echo "$(date +%s.%N) - $t0" | bc | cut -c1-5) s: $r"; }
echo "== plugin running:"; call
STOPCMD=""
[ "$MODE" = finalized ] && STOPCMD='call (void) gnome_settings_manager_stop (gnome_settings_manager_new ())'
cat > /tmp/pas.gdb <<G
set pagination off
set breakpoint pending on
set confirm off
handle SIGCONT nostop noprint pass
$STOPCMD
echo GDB-READY\n
dprintf handle_method_call,"CB handle_method_call %s manager=%p\n", method_name, user_data
dprintf idle_triggered_idle_cb,"CB idle_triggered_idle_cb watch=%u manager=%p\n", watch_id, user_data
dprintf idle_became_active_cb,"CB idle_became_active_cb manager=%p\n", user_data
dprintf idle_set_mode,"CB idle_set_mode mode=%d\n", mode
continue
echo AFTER-CONTINUE\n
bt 8
G
[ "$MODE" = stopped ] && { gsettings set $S active false; sleep 3; }
T=$(date +%T)
sudo -n timeout 150 stdbuf -oL gdb -q -batch -p $P -x /tmp/pas.gdb > /tmp/pas.txt 2>&1 &
G=$!
sleep 10
echo "== after stop ($MODE):"; call
echo "== 30 s without input"; sleep 30
echo "== pointer moved"; xdotool mousemove_relative 40 40; sleep 3; xdotool mousemove_relative -- -40 -40; sleep 5
sudo -n kill -INT $G 2>/dev/null; sleep 2; wait $G 2>/dev/null
grep -E "^CB |GDB-READY|AFTER-CONTINUE|SIGSEGV|SIGABRT|signal SIG|^#[0-9]" /tmp/pas.txt | cut -c1-170 | uniq -c | head -30
echo "u-s-d pid $P alive: $(kill -0 $P 2>/dev/null && echo yes || echo no); criticals since $T: $(journalctl --since $T --no-pager | grep -c 'unity-settings-daemon.*\(CRITICAL\|assertion\)')"
journalctl --since $T --no-pager | grep 'unity-settings-daemon.*\(CRITICAL\|assertion\|WARNING\)' | cut -c40-190 | sort | uniq -c | head -8
echo "crash reports: $(ls /var/crash | grep -c unity-settings)"
[ "$MODE" = stopped ] && gsettings set $S active true
gsettings set $S sleep-inactive-ac-type "$OLDT"; gsettings set $S sleep-inactive-ac-timeout "$OLDS"
