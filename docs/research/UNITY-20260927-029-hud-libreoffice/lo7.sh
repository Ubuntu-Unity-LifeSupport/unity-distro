#!/bin/bash
# lo7.sh N - bamfwatch.py per run; GAP = seconds after the old soffice.bin exits, WATCH_DELAY = seconds between starting the watcher and Writer (/tmp/bamf-N.txt)
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
for r in $(seq "${1:-5}"); do
  pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep ${GAP:-3}
  since=$(date "+%F %T")
  python3 ~/b029/bamfwatch.py > ~/b029/bamf-$(date +%H%M%S)-$r.txt 2>&1 & mon=$!
  sleep ${WATCH_DELAY:-1}
  P=$(pgrep -x compiz)
  (cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "libreoffice --writer --norestore") > ~/.ht-args
  xargs -0 -a ~/.ht-args env -i > ~/app-lo.log 2>&1 < /dev/null &
  i=0; while ! xdotool search --onlyvisible --name "LibreOffice Writer" >/dev/null 2>&1 && [ $i -lt 90 ]; do sleep 1; i=$((i+1)); done
  sleep 8
  kill $mon
  w=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1)
  xdotool windowactivate --sync "$w"; sleep 2
  stack=$(gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack)
  inst=$(echo "$stack" | grep -c "$w")
  appid=$(echo "$stack" | grep -o "$w, '[^']*'" | head -1 | sed "s/.*, '//; s/'$//")
  h1=$(gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud.StartQuery "Сохранить" 5 2>/dev/null | grep -c "(Файл)"); sleep 5
  h2=$(gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud.StartQuery "Сохранить" 5 2>/dev/null | grep -c "(Файл)")
  nodesk=$(journalctl --user --since "$since" --no-pager -u window-stack-bridge.service 2>/dev/null | grep -c "Could not get desktop file")
  echo "run $r: xid=$w in_window_stack=$inst app_id=$appid hud_now=$h1 hud_after_5s=$h2 no_desktop_file=$nodesk"
done
