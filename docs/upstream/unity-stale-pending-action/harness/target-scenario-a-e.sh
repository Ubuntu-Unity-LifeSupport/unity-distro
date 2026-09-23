#!/bin/sh
# Runs on target as mike: sh target-scenario-a-e.sh TAG   (xdotool installed; logs in /tmp/sc-TAG)
# scenario.sh TAG - steps A-E of the #2 reproduction, a screenshot after each.
T=$1; O=/tmp/sc-$T; rm -rf $O; mkdir -p $O; export DISPLAY=:0
dbus-monitor --session "interface='org.gnome.SessionManager.EndSessionDialog'" "interface='org.gnome.SessionManager',member='Shutdown'" > $O/dbus.log 2>&1 &
M=$!; sleep 1
shot() { sleep 4; gnome-screenshot -f $O/$1.png 2>/dev/null; echo "$1 $(date '+%T')" >> $O/steps; }
menu() { xdotool mousemove 1253 14 click 1; sleep 2; xdotool mousemove 1100 234 click 1; }
date '+start %F %T' > $O/steps
menu;                                  shot A-menu-shutdown
xdotool mousemove 717 448 click 1;     shot B-confirm-in-unity
xdotool key Escape;                    shot C-escape-cinnamon
menu;                                  shot D-menu-again
xdotool key Escape; sleep 1; menu;     shot E-menu-once-more
xdotool key Escape; sleep 1
kill $M
journalctl --user -b --since "$(head -1 $O/steps | cut -d' ' -f2-)" -o short-precise 2>/dev/null | grep -i -E 'unity.*(Open request|stale|pending|Dropping)|GnomeSessionManager' > $O/journal.log
cat $O/steps
