#!/bin/bash
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
rm -f /tmp/gt.in; mkfifo /tmp/gt.in
(env -i "${envs[@]}" $HOME/b/groupstest < /tmp/gt.in > /tmp/gt.out 2>&1 &) ; exec 3>/tmp/gt.in
sleep 5
w=$(xdotool search --onlyvisible --name '^groupstest$' | tail -1)
bus=$(xprop -id $w _GTK_UNIQUE_BUS_NAME | sed -n 's/.*= "\(.*\)"/\1/p')
wp=$(xprop -id $w _GTK_WINDOW_OBJECT_PATH | sed -n 's/.*= "\(.*\)"/\1/p')
names() { gdbus call --session -d $bus -o $wp -m org.gtk.Actions.List | grep -o "gtk-nocsd-grp-[a-z]*" | sort | tr '\n' ' '; }
desc() { gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Describe gtk-nocsd-grp-$1 2>&1 | cut -c1-50; }
act() { gdbus call --session -d $bus -o $wp -m org.gtk.Actions.Activate gtk-nocsd-grp-$1 '[]' '{}' >/dev/null 2>&1; sleep 1; }
echo "before insert: [$(names)]"
echo i >&3; sleep 1; echo "after insert:  [$(names)] hello=$(desc hello) toggle=$(desc toggle)"
act hello; act toggle; echo "toggle now $(desc toggle)"
echo d >&3; sleep 1; echo "after disable: hello=$(desc hello)"
echo r >&3; sleep 1; echo "after remove:  [$(names)]"
echo i >&3; sleep 1; echo "after re-insert: [$(names)] hello=$(desc hello)"; act hello
exec 3>&-; sleep 1
grep -E "ACTIVATED|INSERTED|REMOVED|DISABLED|CRITICAL" /tmp/gt.out
pkill -x groupstest
