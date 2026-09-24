#!/bin/sh
# Logout cycle run by root (systemd-run), so that mike has no session but
# the graphical one - as a real user would. Acts on the desktop as mike
# without PAM (setpriv). Results in /home/mike/lo/N/.
N=$1; D=/home/mike/lo/$N; mkdir -p $D; chown mike:mike /home/mike/lo $D
M="setpriv --reuid=mike --regid=mike --init-groups env HOME=/home/mike DISPLAY=:0 XAUTHORITY=/home/mike/.Xauthority"
log() { echo "$(date +%T.%3N) $*" >> $D/steps; }
sleep 15
log "cycle $N start; mike sessions: $(loginctl list-sessions --no-legend | awk '$3=="mike"{print $1"/"$4"/"$5}' | tr '\n' ' ') user@1000=$(systemctl is-active user@1000.service)"
T=$(date +%T)
ls /var/crash > $D/crash-before
$M gnome-screenshot -f $D/1-before.png 2>/dev/null
$M xdotool key ctrl+alt+Delete; sleep 3
$M gnome-screenshot -f $D/2-dialog.png 2>/dev/null
log "click 728 458"
$M xdotool mousemove 728 458 click 1
sleep 40
log "after logout: seat0=$(loginctl list-sessions --no-legend | awk '$4=="seat0"{print $1"/"$3}') user@1000=$(systemctl is-active user@1000.service) compiz=$(pgrep -x compiz)"
journalctl --since $T --no-pager -o short-iso > $D/journal-logout.txt
ls /var/crash > $D/crash-after-logout
T2=$(date +%T)
systemctl restart lightdm
sleep 90
log "after relogin: seat0=$(loginctl list-sessions --no-legend | awk '$4=="seat0"{print $1"/"$3}') user@1000=$(systemctl is-active user@1000.service) compiz=$(pgrep -x compiz) nemo-desktop=$(pgrep -x nemo-desktop)"
$M gnome-screenshot -f $D/3-relogin.png 2>/dev/null
journalctl --since $T2 --no-pager -o short-iso > $D/journal-relogin.txt
ls /var/crash > $D/crash-after-relogin
log "logout bad lines: $(grep -c -E 'segfault|general protection|core-dump|dumped' $D/journal-logout.txt); relogin activation timeouts: $(grep -c -E 'Failed to activate service.*timed out|Timed out waiting for proxy' $D/journal-relogin.txt); crash: $(cat $D/crash-after-relogin | tr '\n' ' ')"
chown -R mike:mike $D
