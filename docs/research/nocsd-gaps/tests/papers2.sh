#!/bin/bash
# papers2.sh LIB: Papers start page, then a PDF opened in the same window, then started with a PDF
T=$(sed -n 's/^T=//p' ~/b/variant.sh | head -1); T=${T:-/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0}
sudo -n cp "$1" $T.new && sudo -n mv $T.new $T
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0
top() { python3 ~/b/audit.py $1 $2 2>&1 | grep -E "^ {2,12}(ok|disabled|MISSING|-)|NO-" | sed 's/  */ /g' | cut -c1-32 | tr '\n' ';' | cut -c1-400; echo; }
pkill -x papers; sleep 1
env -i "${envs[@]}" papers > /tmp/pap.out 2>&1 & p=$!; sleep 7
w=$(xdotool search --onlyvisible --pid $p | tail -1)
echo "START: $(top $p $w)"
xdotool windowactivate --sync $w; sleep 1; xdotool key ctrl+o; sleep 3
xdotool key ctrl+l; sleep 1; xdotool type --delay 30 "$HOME/b/test.pdf"; sleep 1; xdotool key Return; sleep 5
echo "SAME WINDOW, PDF OPENED: $(top $p $w)"
kill $p; sleep 1
env -i "${envs[@]}" papers ~/b/test.pdf > /tmp/pap3.out 2>&1 & q=$!; sleep 8
w=$(xdotool search --onlyvisible --pid $q | tail -1)
echo "STARTED WITH PDF: $(top $q $w)"
kill $q
