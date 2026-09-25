#!/bin/sh
# cinnamon-session #214 on Unity: reboot from Unity's menu while a delay
# inhibitor is held (InhibitDelayMaxSec=60). Run as root via systemd-run.
# The machine reboots; read the result from `journalctl -b -1`.
M="setpriv --reuid=mike --regid=mike --init-groups env HOME=/home/mike DISPLAY=:0 XAUTHORITY=/home/mike/.Xauthority"
mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nInhibitDelayMaxSec=60\n' > /etc/systemd/logind.conf.d/zz-delaytest.conf
systemctl restart systemd-logind; sleep 5
systemd-inhibit --what=shutdown --mode=delay --who=delaytest --why=delaytest sleep 600 &
sleep 2
logger -t delaytest "cinnamon-session $(dpkg-query -W -f='${Version}' cinnamon-session); inhibitors: $(systemd-inhibit --list --no-legend | grep -c delaytest)"
$M xdotool mousemove 1253 14 click 1; sleep 1.5
$M xdotool mousemove 1100 234 click 1; sleep 3
logger -t delaytest "clicking Перезагрузить"
$M xdotool mousemove 566 448 click 1
for i in $(seq 1 70); do
  logger -t delaytest "t=$i seat0=$(loginctl list-sessions --no-legend | awk '$4=="seat0"{print $1"/"$3}') compiz=$(pgrep -x compiz) csm=$(pgrep -f '[c]innamon-session-binary' | head -1)"
  sleep 1
done
