#!/bin/sh
# UNITY-20261002-011 / -003 (target test of +unity11): 27 minutes of real
# idle time on AC with the override in place; does u-s-d's idle policy
# suspend the machine? Conditions (recorded in the run file):
#  - gnome.is_vm=0 on the kernel command line (otherwise u-s-d makes every
#    idle transition a no-op on a VM);
#  - SessionIsActive is real (cinnamon-session +unity4 on target);
#  - light-locker's lock after the screensaver is switched off for the run
#    (apps.light-locker lock-after-screensaver 0), so the session stays
#    active: with the lock, light-locker would switch to the greeter at 5 min,
#    the session would go inactive and u-s-d would drop all idle watches -
#    "no suspend" would then not be the override's doing. Restored after.
# Evidence: gdb dprintf on idle_set_mode / idle_triggered_idle_cb /
# idle_configure for the whole time (ended with SIGINT), the session VT and
# SessionIsActive every minute, and logind's suspend messages.
# Run as the session user through ssh, nohup'd; output /tmp/ac27.txt.
. ~/envt.sh
S=com.canonical.unity.settings-daemon.plugins.power
O=/tmp/ac27.txt
P=$(pgrep -x unity-settings- | head -1)
LL=$(gsettings get apps.light-locker lock-after-screensaver)
{
echo "start $(date -u +%FT%TZ): u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P, cinnamon-session $(dpkg-query -W -f='${Version}' cinnamon-session)"
echo "cmdline: $(grep -o 'gnome.is_vm=[01]' /proc/cmdline)"
echo "effective: sleep-inactive-ac-timeout=$(gsettings get $S sleep-inactive-ac-timeout) ac-type=$(gsettings get $S sleep-inactive-ac-type) idle-dim=$(gsettings get $S idle-dim) session idle-delay=$(gsettings get org.gnome.desktop.session idle-delay)"
echo "light-locker lock-after-screensaver was $LL, set to 0 for the run"
} > $O
gsettings set apps.light-locker lock-after-screensaver 0
cat > /tmp/ac27.gdb <<'G'
set pagination off
set confirm off
set breakpoint pending on
handle SIGPIPE nostop noprint pass
handle SIGTERM nostop noprint pass
break idle_set_mode
commands
  silent
  printf "SET-MODE %d (current %d)\n", mode, manager->priv->current_idle_mode
  continue
end
break idle_triggered_idle_cb
commands
  silent
  printf "IDLE-CB watch=%u\n", watch_id
  continue
end
continue
G
sudo -n timeout -s INT 1700 gdb -q -batch -p $P -x /tmp/ac27.gdb > /tmp/ac27-gdb.txt 2>&1 &
G=$!
sleep 3
for m in $(seq 1 27); do
  sleep 60
  echo "min $m $(date +%T): VT $(sudo -n fgconsole) SessionIsActive=$(busctl --user get-property org.gnome.SessionManager /org/gnome/SessionManager org.gnome.SessionManager SessionIsActive 2>&1 | tr -d '\n') screensaver=$(gdbus call --session --dest org.gnome.ScreenSaver --object-path /org/gnome/ScreenSaver --method org.gnome.ScreenSaver.GetActive 2>&1 | tr -d '\n')" >> $O
done
sudo -n pkill -INT -x gdb 2>/dev/null; wait $G 2>/dev/null
gsettings set apps.light-locker lock-after-screensaver "$LL"
{
echo "end $(date -u +%FT%TZ); light-locker lock-after-screensaver restored to $(gsettings get apps.light-locker lock-after-screensaver)"
echo "--- logind suspend messages during the run:"
journalctl -b --no-pager -o short-precise --since "-28min" 2>/dev/null | grep -i -E "will suspend|suspend|sleep" | grep -v -i "inhibit" | head
echo "--- gdb events:"
grep -E "SET-MODE|IDLE-CB|SIG|rror" /tmp/ac27-gdb.txt
echo "uptime: $(uptime)"
} >> $O
