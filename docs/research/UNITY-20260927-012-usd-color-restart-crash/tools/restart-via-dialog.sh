#!/bin/sh
# UNITY-20260927-012 (from UNITY-20260927-009): one restart through Unity's end-session dialog, the path
# on which compiz's XSMP "die" used to crash it in exit() (research/
# shutdown-path, "Option A ... and a compiz exit race"). Run as root through
# systemd-run. Any core is written by the kernel to /var/tmp (apport's own
# cores were cut short by the reboot); read with tools/restart-check.sh after
# the next boot. Clicks as in research/cinnamon-session-214-202/runs/cs-delay.sh.
M="setpriv --reuid=mike --regid=mike --init-groups env HOME=/home/mike DISPLAY=:0 XAUTHORITY=/home/mike/.Xauthority"
sysctl -q kernel.core_pattern=/var/tmp/core.%e.%p.%t
logger -t u009 "restart via dialog; compiz $(dpkg-query -W -f='${Version}' compiz-core); pid $(pgrep -x compiz); core_pattern $(cat /proc/sys/kernel/core_pattern)"
$M xdotool mousemove 1253 14 click 1; sleep 1.5
$M xdotool mousemove 1100 234 click 1; sleep 3
logger -t u009 "clicking Перезагрузить"
$M xdotool mousemove 566 448 click 1
