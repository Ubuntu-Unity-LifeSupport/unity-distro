#!/bin/sh
# UNITY-20260927-003: reboot or power off the Unity session while another
# process holds a logind delay inhibitor (InhibitDelayMaxSec=60), and log
# once a second whether the session is still there.
# Usage (on target, as root): systemd-run --unit=csdelay sh cs-delay.sh reboot|poweroff
#   reboot   - clicks Unity's menu -> "Выключить..." -> "Перезагрузить"
#              (same clicks as research/cinnamon-session-214-202/runs/cs-delay.sh)
#   poweroff - calls org.gnome.SessionManager.Shutdown() on mike's session bus,
#              then clicks the power button of the dialog Unity shows for it
# The machine goes down; read the result from `journalctl -b -1`
# (tools/cs-extract.sh).
set -u
ACTION=${1:?reboot or poweroff}
M="setpriv --reuid=mike --regid=mike --init-groups env HOME=/home/mike DISPLAY=:0 XAUTHORITY=/home/mike/.Xauthority DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nInhibitDelayMaxSec=60\n' > /etc/systemd/logind.conf.d/zz-delaytest.conf
systemctl restart systemd-logind; sleep 5
# logind's side: the Reboot/PowerOff calls, its replies and errors, and
# PrepareForShutdown (read by tools/cs-extract.sh after the next boot)
busctl monitor --system \
  --match="type=method_call,interface=org.freedesktop.login1.Manager" \
  --match="type=method_return,sender=org.freedesktop.login1" \
  --match="type=error" \
  --match="type=signal,member=PrepareForShutdown" > /var/tmp/cs-busmon.txt 2>&1 &
systemd-inhibit --what=shutdown --mode=delay --who=delaytest --why=delaytest sleep 600 &
sleep 2
logger -t delaytest "action=$ACTION cinnamon-session $(dpkg-query -W -f='${Version}' cinnamon-session); inhibitors: $(systemd-inhibit --list --no-legend | grep -c delaytest)"
case "$ACTION" in
reboot)
  $M xdotool mousemove 1253 14 click 1; sleep 1.5
  $M xdotool mousemove 1100 234 click 1; sleep 3
  logger -t delaytest "clicking Перезагрузить"
  $M xdotool mousemove 566 448 click 1
  ;;
poweroff)
  logger -t delaytest "calling org.gnome.SessionManager.Shutdown"
  $M gdbus call --session --dest org.gnome.SessionManager \
    --object-path /org/gnome/SessionManager \
    --method org.gnome.SessionManager.Shutdown &
  sleep 3
  # Shutdown() asks Unity for its end-session dialog; click its power button
  logger -t delaytest "clicking Выключить"
  $M xdotool mousemove 881 407 click 1
  ;;
*) echo "unknown action $ACTION" >&2; exit 2 ;;
esac
for i in $(seq 1 70); do
  logger -t delaytest "t=$i seat0=$(loginctl list-sessions --no-legend | awk '$4=="seat0"{print $1"/"$3}') compiz=$(pgrep -x compiz) csm=$(pgrep -x cinnamon-sessio | head -1)"
  sleep 1
done
