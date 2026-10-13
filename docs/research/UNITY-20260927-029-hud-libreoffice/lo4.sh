#!/bin/bash
# lo4.sh N - UNITY-20260927-029: start LibreOffice Writer N times in the session environment; per run:
# is its window in window-stack-bridge's stack, does HUD answer "Сохранить", and what hud-service and
# window-stack-bridge logged meanwhile.
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
q() { gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud \
      --method com.canonical.hud.StartQuery "Сохранить" 5 2>/dev/null | grep -c "(Файл)"; }
for r in $(seq "${1:-5}"); do
  pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep 3
  since=$(date "+%F %T")
  P=$(pgrep -x compiz)
  (cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "libreoffice --writer --norestore") > ~/.ht-args
  xargs -0 -a ~/.ht-args env -i > ~/app-lo.log 2>&1 < /dev/null &
  i=0; while ! xdotool search --onlyvisible --name "LibreOffice Writer" >/dev/null 2>&1 && [ $i -lt 90 ]; do sleep 1; i=$((i+1)); done
  sleep 8
  w=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1)
  xdotool windowactivate --sync "$w"; sleep 2
  inst=$(gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack | grep -c "$w")
  h1=$(q); sleep 5; h2=$(q)
  illegal=$(journalctl --user --since "$since" --no-pager -u hud.service 2>/dev/null | grep -c "Illegal arguments when updating GMenuModel")
  nodesk=$(journalctl --user --since "$since" --no-pager -u window-stack-bridge.service 2>/dev/null | grep -c "Could not get desktop file")
  echo "run $r: xid=$w in_window_stack=$inst hud_now=$h1 hud_after_5s=$h2 illegal_args=$illegal no_desktop_file=$nodesk"
done
echo "hud-service pid: $(pgrep -x hud-service)"
