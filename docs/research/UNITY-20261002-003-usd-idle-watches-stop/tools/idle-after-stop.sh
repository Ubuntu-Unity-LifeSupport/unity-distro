#!/bin/sh
# UNITY-20261002-003: do the power plugin's idle watches outlive stop()?
# Before F2 exists, SessionIsActive is forced through the session proxy's
# cache (Design Challenger G5), in one gdb session (two debuggers cannot
# attach to one process): at the first idle_configure() after the plugin's
# start(), gdb sets priv->is_virtual_machine = 0 (the VM makes idle_set_mode
# a no-op) and calls g_dbus_proxy_set_cached_property (priv->session,
# "SessionIsActive", TRUE); idle_configure then adds the watches. With the
# idle delay set to 5 s, the plugin is switched off through its GSettings
# key and gdb records the idle callbacks that still run after stop():
# idle_triggered_idle_cb / idle_became_active_cb (> 0 = the watches
# outlived stop()). Needs u-s-d dbgsym; gdb as root (ptrace scope).
# Output: /tmp/u003.txt and /tmp/u003-gdb.txt.
. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.power
P=$(pgrep -x unity-settings- | head -1)
O=/tmp/u003.txt
echo "u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P $(date +%T)" > $O
gsettings set org.gnome.desktop.session idle-delay 5
gsettings set $S idle-dim true
# the VM has no backlight and no screensaver: dim and blank watches are never
# added; the sleep watch is, so make it fire soon and harmlessly (blank, not suspend)
# type first: with the idle path live (gnome.is_vm=0 and a real SessionIsActive)
# a timeout set while the type is still the default suspended the machine once
gsettings set $S sleep-inactive-ac-type blank
gsettings set $S sleep-inactive-ac-timeout 15
gsettings set $S active true; sleep 2
cat > /tmp/u003.gdb <<'G'
set pagination off
set confirm off
set breakpoint pending on
handle SIGPIPE nostop noprint pass
handle SIGTERM nostop noprint pass
set $forced = 0
break gsd_power_manager_start
commands
  silent
  printf "START\n"
  continue
end
break idle_configure
commands
  silent
  if $forced == 0 && manager->priv->session != 0
    set var manager->priv->is_virtual_machine = 0
    # glib has no debug info here: cast the callees to their types
    call ((void (*)(GDBusProxy *, const char *, GVariant *)) g_dbus_proxy_set_cached_property) (manager->priv->session, "SessionIsActive", ((GVariant *(*)(int)) g_variant_new_boolean) (1))
    set $forced = 1
    printf "FORCED cached SessionIsActive=1, is_virtual_machine=0\n"
    # later hits are inlined call sites where manager is optimized out: stop watching here
    delete 2
  end
  continue
end
break idle_triggered_idle_cb
commands
  silent
  printf "IDLE-CB watch=%u\n", watch_id
  continue
end
break idle_became_active_cb
commands
  silent
  printf "ACTIVE-CB\n"
  continue
end
break idle_set_mode
commands
  silent
  printf "SET-MODE %d (current %d)\n", mode, manager->priv->current_idle_mode
  continue
end
break gsd_power_manager_stop
commands
  silent
  printf "STOP dim=%u blank=%u sleep=%u warn=%u user_active=%u mode=%d vm=%d\n", manager->priv->idle_dim_id, manager->priv->idle_blank_id, manager->priv->idle_sleep_id, manager->priv->idle_sleep_warning_id, manager->priv->idle_user_active_id, manager->priv->current_idle_mode, manager->priv->is_virtual_machine
  continue
end
continue
G
# end gdb with SIGINT (it stops the inferior and detaches, removing its
# breakpoints); SIGTERM left an int3 behind once and u-s-d died of SIGTRAP
sudo -n timeout -s INT 200 gdb -q -batch -p $P -x /tmp/u003.gdb > /tmp/u003-gdb.txt 2>&1 &
G=$!
sleep 5
# restart the plugin so that start() and its idle_configure run under gdb
gsettings set $S active false; sleep 3; gsettings set $S active true; sleep 6
echo "plugin restarted under gdb at $(date +%T); after start: $(grep -c FORCED /tmp/u003-gdb.txt) forced" >> $O
sleep 10
echo "watches state is printed at STOP; plugin off at $(date +%T)" >> $O
gsettings set $S active false
sleep 3
# an idle watch fires once per idle period: reset the idle time with real input
# right after the stop, then wait longer than the 15 s timeout
N=$(grep -l "ImExPS/2" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5)
sudo ~/evinject.py /dev/input/$N 8 4 2 >/dev/null 2>&1 && echo "input injected at $(date +%T) (idle reset after stop)" >> $O
sleep 25
echo "25 s after the input: $(date +%T)" >> $O
sudo ~/evinject.py /dev/input/$N 8 4 2 >/dev/null 2>&1 && echo "input injected again" >> $O
sleep 5
gsettings set $S active true
gsettings reset org.gnome.desktop.session idle-delay
gsettings reset $S sleep-inactive-ac-timeout; gsettings reset $S sleep-inactive-ac-type
sleep 3
sudo -n pkill -INT -x gdb 2>/dev/null; wait $G 2>/dev/null
echo "--- gdb events:" >> $O
grep -E "START|FORCED|IDLE-CB|ACTIVE-CB|SET-MODE|STOP|SIG|rror|ptrace|optimized" /tmp/u003-gdb.txt >> $O
echo "callbacks after the last STOP: $(awk '/^STOP/{n=0;s=1;next} s&&/-CB/{n++} END{print n+0}' /tmp/u003-gdb.txt)" >> $O
cat $O
