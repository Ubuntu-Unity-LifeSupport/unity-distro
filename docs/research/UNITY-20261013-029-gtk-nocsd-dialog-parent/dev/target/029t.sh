# UNITY-20261013-029 target test: epiphany with the default-browser question, SIGTERM; the session's preload
echo "== $(date +%T) libgtk-nocsd0 $(dpkg-query -W -f='${Version}' libgtk-nocsd0); compiz LD_PRELOAD: $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | sed -n 's/^LD_PRELOAD=//p')"
echo "default http handler: $(env -i $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep -E '^(XDG_DATA_DIRS|HOME|XDG_CONFIG_HOME|DBUS_SESSION_BUS_ADDRESS)=') gio mime x-scheme-handler/http | head -1)"
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
for r in 1 2 3 4 5; do
  pkill -x epiphany; for i in $(seq 30); do pgrep -x epiphany > /dev/null || break; sleep 1; done
  env -i "${envs[@]}" epiphany > /tmp/epi-t$r.err 2>&1 & p=$!
  sleep 15
  maps=$(grep -c libgtk-nocsd /proc/$p/maps)
  wins=$(for w in $(DISPLAY=:0 xdotool search --all --pid $p --name '.*' 2>/dev/null); do DISPLAY=:0 xdotool getwindowname $w 2>/dev/null; done | grep -v '^$' | tr '\n' '|')
  kill -TERM $p; wait $p; rc=$?
  echo "run $r: nocsd mapped $maps; windows: $wins; exit $rc$([ $rc = 134 ] && echo ' (SIGABRT)')"
  grep -E "ERROR|CRITICAL" /tmp/epi-t$r.err | head -2 | sed 's/^/    /'
done
echo "crash files: $(ls -la --time-style=+%T /var/crash/ | grep -c epiphany)"
