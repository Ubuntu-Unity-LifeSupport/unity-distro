#!/bin/sh
# Runs on target as mike. RESTARTS an unfixed machine; logs go to ~/sc-residual.
# residual.sh - pending REBOOT, then the menu's Open(2). Logs survive a reboot.
O=$HOME/sc-residual; rm -rf $O; mkdir -p $O; export DISPLAY=:0
dbus-monitor --session "interface='org.gnome.SessionManager.EndSessionDialog'" "interface='org.gnome.SessionManager'" > $O/dbus-session.log 2>&1 &
M1=$!
sudo -n dbus-monitor --system "interface='org.freedesktop.login1.Manager'" > $O/dbus-system.log 2>&1 &
M2=$!; sleep 1
st() { echo "$1 $(date '+%T.%N' | cut -c1-12) quit-dialog:$(pgrep -f cinnamon-session-quit >/dev/null && echo alive || echo gone)" >> $O/steps; sync; }
shot() { sleep 3; gnome-screenshot -f $O/$1.png 2>/dev/null; st $1; }
date '+start %F %T' > $O/steps
xdotool mousemove 1253 14 click 1; sleep 2; xdotool mousemove 1100 234 click 1;  shot R1-menu
xdotool mousemove 566 448 click 1;                                              shot R2-reboot-in-unity
xdotool key Escape;                                                             shot R3-escape-cinnamon
xdotool mousemove 1253 14 click 1;                                              shot R4a-indicator-open
xdotool mousemove 1100 234 click 1; st R4b-clicked; sleep 1; gnome-screenshot -f $O/R4c.png; st R4c; sleep 5; st R4d-after5s
xdotool key Escape; sleep 1
kill $M1; sudo -n kill $M2; st end
