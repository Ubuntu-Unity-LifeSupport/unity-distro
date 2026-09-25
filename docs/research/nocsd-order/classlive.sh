#!/bin/bash
# classtest in the live session: stand-in for win.class-hello follows gtk_widget_action_set_enabled
pid=$(pgrep -x compiz | head -1)
mapfile -d '' envs < /proc/$pid/environ
export $(tr '\0' '\n' < /proc/$pid/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
env -i "${envs[@]}" $HOME/b/classtest > $HOME/b/live/classtest.out 2>&1 & app=$!; sleep 6
w=$(xdotool search --onlyvisible --name '^classtest$' | tail -1)
bus=$(xprop -id $w _GTK_UNIQUE_BUS_NAME | sed -n 's/.*= "\(.*\)"/\1/p')
wp=$(xprop -id $w _GTK_WINDOW_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
echo "maps: $(grep -oE 'lib(unity-gtk4-menu|gtk-nocsd)\.so\.0' /proc/$app/maps | sort -u | tr '\n' ' ')"
st() { gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Describe "unity-gtk4-menu-win-class-$1" | cut -c1-40; }
echo "class-hello stand-in: $(st hello)"; echo "class-off stand-in:   $(st off)"
gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Activate toggle-hello '[]' '{}' >/dev/null; sleep 1
echo "after toggle-hello:   $(st hello)"
gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Activate unity-gtk4-menu-win-class-hello '[]' '{}' >/dev/null
gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Activate toggle-hello '[]' '{}' >/dev/null; sleep 1
echo "after 2nd toggle:     $(st hello)"
gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Activate unity-gtk4-menu-win-class-hello '[]' '{}' >/dev/null; sleep 1
xdotool windowactivate --sync $w; sleep 1; xdotool mousemove 90 12 sleep 1 click 1; sleep 2
import -window root $HOME/b/live/classtest-menu.png; xdotool key Escape
echo "-- app stdout:"; cat $HOME/b/live/classtest.out | grep -vE '^\s*$' | tail -6
kill $app
