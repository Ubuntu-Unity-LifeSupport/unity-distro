#!/bin/sh
# UNITY-20260928-022: after the forced finalize, call the power object through
# u-s-d's unique bus name (the well-known name is released by then), so the
# call reaches the connection: GDBus must answer from the registration table
# (object gone) instead of dispatching to freed memory. Run as mike over ssh
# with the perturb drop-in.
. ~/envt.sh
P=$(pgrep -x unity-settings- | head -1)
U=$(gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetNameOwner org.gnome.SettingsDaemon.Power | grep -o ":[0-9.]*")
echo "u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P unique name $U"
cat > /tmp/fu.gdb <<'G'
set pagination off
set confirm off
handle SIGCONT nostop noprint pass
call (void) gnome_settings_manager_stop (gnome_settings_manager_new ())
echo STOP-CALLED\n
continue
echo AFTER-CONTINUE\n
bt 6
G
sudo -n timeout 40 stdbuf -oL gdb -q -batch -p $P -x /tmp/fu.gdb > /tmp/fu.txt 2>&1 &
G=$!
sleep 12
for m in org.gnome.SettingsDaemon.Power.Screen.GetPercentage org.freedesktop.DBus.Properties.Get; do
  a=""; [ $m = org.freedesktop.DBus.Properties.Get ] && a="org.gnome.SettingsDaemon.Power Percentage"
  echo "  $m via $U: $(timeout 30 gdbus call --session --dest $U --object-path /org/gnome/SettingsDaemon/Power --method $m $a 2>&1 | head -1 | cut -c1-120)"
done
sleep 3; sudo -n kill -INT $G 2>/dev/null; wait $G 2>/dev/null
grep -E "STOP-CALLED|AFTER-CONTINUE|SIGSEGV|SIGABRT|^#0" /tmp/fu.txt | cut -c1-140
echo "u-s-d pid $P alive: $(kill -0 $P 2>/dev/null && echo yes || echo no); crash reports: $(ls /var/crash | grep -c unity-settings)"
