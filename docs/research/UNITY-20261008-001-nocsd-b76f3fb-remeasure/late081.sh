#!/bin/bash
# late081.sh NAME LIB VAR - the late-menu scenarios of research/nocsd-gaps (naut.sh, papers2.sh) with LIB as
# libgtk-nocsd.so.0 and VAR (e.g. GTK_NOCSD_MENU=1) added to each start: Nautilus Undo before and after a
# rename over D-Bus; Papers on its start page and started with a PDF. The same-window Papers step (a PDF
# opened through the file chooser) is not run: in UNITY-20260927-034 it needed a hand step.
set -u
name=$1; lib=$2; var=$3
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
sudo -n cp "$lib" $T.new && sudo -n mv $T.new $T
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
top() { python3 ~/b/audit.py "$@" 2>&1 | grep -E "^ {0,12}(ok|disabled|MISSING|-)|NO-|^ +- " | sed 's/  */ /g' | cut -c1-48 | tr '\n' ';' | cut -c1-600; echo; }
echo "#### $name ($var)"
pkill -x nautilus; sleep 1
rm -f ~/b/rename-*.txt; echo x > ~/b/rename-a.txt
env -i "${envs[@]}" $var nautilus ~/b > /tmp/naut.out 2>&1 & p=$!
sleep 8
labels() { python3 ~/b/audit.py $p 2>&1 | grep -iE "undo|redo|отмен|повтор" | sed 's/  */ /g' | tr '\n' ';'; }
echo "nautilus before: $(labels)"
gdbus call --session -d org.gnome.Nautilus -o /org/gnome/Nautilus/FileOperations2 -m org.gnome.Nautilus.FileOperations2.RenameURI "file://$HOME/b/rename-a.txt" "rename-b.txt" '{}' >/dev/null 2>&1
sleep 3
echo "nautilus after rename: $(labels) files: $(ls ~/b/rename-*.txt | xargs -n1 basename | tr '\n' ' ')"
kill $p; sleep 1
pkill -x papers; sleep 1
env -i "${envs[@]}" $var papers > /tmp/pap.out 2>&1 & p=$!; sleep 7
w=$(xdotool search --onlyvisible --pid $p | tail -1)
echo "papers start page: $(top $p $w)"
kill $p; sleep 1
env -i "${envs[@]}" $var papers ~/b/test.pdf > /tmp/pap3.out 2>&1 & q=$!; sleep 8
w=$(xdotool search --onlyvisible --pid $q | tail -1)
echo "papers started with a PDF: $(top $q $w)"
kill $q; sleep 1
sudo -n cp ~/b081/libgtk-nocsd.so.0.pkg $T.new && sudo -n mv $T.new $T
