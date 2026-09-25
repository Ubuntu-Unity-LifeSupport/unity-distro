#!/bin/bash
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
pkill -x nautilus; sleep 1
rm -f ~/b/rename-*.txt; echo x > ~/b/rename-a.txt
env -i "${envs[@]}" nautilus ~/b > /tmp/naut.out 2>&1 & p=$!
sleep 8
labels() { python3 ~/b/audit.py $p 2>&1 | grep -iE "undo|redo|отмен|повтор" | sed 's/  */ /g' | tr '\n' ';'; }
echo "before: $(labels)"
gdbus call --session -d org.gnome.Nautilus -o /org/gnome/Nautilus/FileOperations2 -m org.gnome.Nautilus.FileOperations2.RenameURI "file://$HOME/b/rename-a.txt" "rename-b.txt" '{}' >/dev/null 2>&1
sleep 3
echo "after rename: $(labels)"
ls ~/b/rename-*.txt
kill $p
