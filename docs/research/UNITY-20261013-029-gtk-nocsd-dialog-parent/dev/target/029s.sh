# start epiphany with the session environment and leave it running; $1 = start|term
if [ "$1" = start ]; then
  sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
  pkill -x epiphany; for i in $(seq 30); do pgrep -x epiphany > /dev/null || break; sleep 1; done
  setsid env -i "${envs[@]}" epiphany > /tmp/epi-s.err 2>&1 < /dev/null & echo $! > /tmp/epi-s.pid
  sleep 12; DISPLAY=:0 wmctrl -l -p 2>/dev/null | grep -w "$(cat /tmp/epi-s.pid)" || DISPLAY=:0 xprop -root _NET_CLIENT_LIST
else
  p=$(cat /tmp/epi-s.pid); kill -TERM $p; for i in $(seq 20); do kill -0 $p 2>/dev/null || break; sleep 1; done
  kill -0 $p 2>/dev/null && echo "still running" || echo "exited"; grep -E "ERROR|CRITICAL" /tmp/epi-s.err | head -2; ls /var/crash
fi
