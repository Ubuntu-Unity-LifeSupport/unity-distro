#!/bin/bash
# nogtk2.sh - restart the Ayatana messages service without GTK2_MODULES, click Pidgin in the menu
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0
pkill -x ayatana-indicat; sleep 1
S=/usr/libexec/ayatana-indicator-messages/ayatana-indicator-messages-service
env -i "${envs[@]}" GTK2_MODULES= setsid nohup $S >/dev/null 2>&1 < /dev/null &
sleep 5
for w in $(xdotool search --onlyvisible --class pidgin); do xdotool windowminimize $w; done; sleep 1
echo "before: $(xdotool getactivewindow getwindowname)"
xdotool mousemove 1120 14 click 1; sleep 2; xdotool mousemove 1125 256; sleep 1; xdotool click 1; sleep 4
echo "after: $(xdotool getactivewindow getwindowname)"
