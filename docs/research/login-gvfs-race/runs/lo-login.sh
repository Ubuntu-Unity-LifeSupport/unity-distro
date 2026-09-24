#!/bin/sh
# Logout + autologin cycles run by root (systemd-run), for the login race.
# Usage: lo-login.sh TAG N...   results in /home/mike/li/TAG-N/
TAG=$1; shift
M="setpriv --reuid=mike --regid=mike --init-groups env HOME=/home/mike DISPLAY=:0 XAUTHORITY=/home/mike/.Xauthority"
sleep 15
for N in "$@"; do
  D=/home/mike/li/$TAG-$N; mkdir -p $D
  log() { echo "$(date +%T.%3N) $*" >> $D/steps; }
  log "cycle $TAG-$N; unity-session $(dpkg-query -W -f='${Version}' unity-session); slow-gvfs drop-in: $(ls /home/mike/.config/systemd/user/gvfs-daemon.service.d/ 2>/dev/null)"
  $M xdotool key ctrl+alt+Delete; sleep 3
  $M xdotool mousemove 728 458 click 1
  sleep 30
  log "after logout: user@1000=$(systemctl is-active user@1000.service)"
  T=$(date +%T)
  systemctl restart lightdm
  sleep 60
  $M gnome-screenshot -f $D/relogin-60s.png 2>/dev/null
  sleep 80
  journalctl --since $T --no-pager -o short-precise > $D/journal.txt
  E=$(grep -A1 "Starting gvfs-daemon.service" $D/journal.txt | grep -c "Stopped gvfs-daemon.service")
  TO=$(grep -c "Failed to activate service 'org.gtk.vfs" $D/journal.txt)
  log "relogin: seat0=$(loginctl list-sessions --no-legend | awk '$4=="seat0"{print $1"/"$3}') early-stops=$E activation-timeouts=$TO nemo-desktop=$(pgrep -x nemo-desktop)"
  chown -R mike:mike /home/mike/li
done
