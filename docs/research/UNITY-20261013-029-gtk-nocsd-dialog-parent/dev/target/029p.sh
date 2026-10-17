# dialogs still work with gtk-nocsd +unity5: answer the question ("ask later"), open/close/reopen Preferences, quit
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
pkill -x epiphany; for i in $(seq 30); do pgrep -x epiphany > /dev/null || break; sleep 1; done
env -i "${envs[@]}" epiphany > /tmp/epi-p2.err 2>&1 & p=$!
sleep 12
DISPLAY=:0 xdotool mousemove 250 320 click 1; sleep 2
echo "question answered: ask-for-default $(env -i "${envs[@]}" gsettings get org.gnome.Epiphany ask-for-default)"
for k in 1 2 3; do
  env -i "${envs[@]}" gapplication action org.gnome.Epiphany preferences; sleep 3
  n=$(DISPLAY=:0 wmctrl -l 2>/dev/null | grep -c "Параметры")
  DISPLAY=:0 xdotool key Escape; sleep 2
  m=$(DISPLAY=:0 wmctrl -l 2>/dev/null | grep -c "Параметры")
  echo "preferences $k: open windows $n, after Escape $m; epiphany alive $(kill -0 $p 2>/dev/null && echo yes || echo no)"
done
kill -TERM $p; wait $p; echo "quit: exit $?"; grep -E "ERROR|CRITICAL" /tmp/epi-p2.err | head -3; ls /var/crash
