#!/bin/sh
# One logout cycle through Unity's dialog, then back in through autologin.
# Usage: logoutcycle.sh N   - logs and screenshots in ~/lo/N/
N=$1; D=~/lo/$N; mkdir -p $D
. ~/envt.sh
T=$(date +%T)
S=$(loginctl list-sessions --no-legend | awk '$4=="seat0"{print $1}')
echo "$T cycle $N session=$S compiz=$(pgrep -x compiz) boot=$(uptime -s)" | tee $D/steps
ls /var/crash > $D/crash-before
gnome-screenshot -f $D/1-before.png 2>/dev/null
xdotool key ctrl+alt+Delete; sleep 3
gnome-screenshot -f $D/2-dialog.png 2>/dev/null
echo "$(date +%T.%3N) click 728 458 Выйти" >> $D/steps
xdotool mousemove 728 458 click 1
sleep 25
echo "$(date +%T.%3N) after 25 s: seat0 session=$(loginctl list-sessions --no-legend | awk '$4=="seat0"{print $1" "$2}') compiz=$(pgrep -x compiz) greeter=$(pgrep -x unity-greeter)" >> $D/steps
journalctl --since $T --no-pager -o short-iso > $D/journal-logout.txt
ls /var/crash > $D/crash-after-logout
sudo -n systemctl restart lightdm
sleep 45
. ~/envt.sh
S2=$(loginctl list-sessions --no-legend | awk '$4=="seat0"{print $1}')
echo "$(date +%T.%3N) after lightdm restart: seat0 session=$S2 compiz=$(pgrep -x compiz)" >> $D/steps
gnome-screenshot -f $D/3-relogin.png 2>/dev/null
ls /var/crash > $D/crash-after-relogin
grep -E "segfault|general protection|core-dump|SEGV|SIGABRT|dumped|g_hash_table|NoCSD|Failed with result|compiz\[.*(Error|error)" $D/journal-logout.txt | cut -c1-220 > $D/journal-bad.txt
echo "bad journal lines: $(wc -l < $D/journal-bad.txt); crash after logout: $(cat $D/crash-after-logout | tr '\n' ' '); after relogin: $(cat $D/crash-after-relogin | tr '\n' ' ')" >> $D/steps
cat $D/steps
