#!/bin/bash
# proptrace.sh OUT - run on target2 in the Unity session. Starts LibreOffice Writer (as lo7.sh does), and
# records, with millisecond timestamps: the window stack bridge's WindowCreated / FocusedWindowChanged
# signals (gdbus monitor), and the first moment each GMenu property (_GTK_UNIQUE_BUS_NAME,
# _GTK_MENUBAR_OBJECT_PATH, _GTK_WINDOW_OBJECT_PATH, _GTK_APPLICATION_OBJECT_PATH) is set on the Writer
# window (xprop polled every 50 ms, from the moment xdotool sees the window, mapped or not). Then one HUD
# query. Output in OUT. The order "WindowCreated before the properties" is the measurement.
set -u
out=${1:?out}
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep 2
ts() { date +%s.%N | cut -c1-14; }
echo "# proptrace $(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id) uptime=$(cut -d' ' -f1 /proc/uptime)" > "$out"
gdbus monitor --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack 2>/dev/null \
  | while IFS= read -r line; do echo "$(ts) BRIDGE $line"; done >> "$out" &
mon=$!
sleep 1
P=$(pgrep -x compiz)
(cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "libreoffice --writer --norestore") > ~/.ht-args
echo "$(ts) START libreoffice --writer" >> "$out"
xargs -0 -a ~/.ht-args env -i > ~/app-lo.log 2>&1 < /dev/null &
w=""; i=0
while [ -z "$w" ] && [ $i -lt 1200 ]; do w=$(xdotool search --class libreoffice 2>/dev/null | while read x; do xprop -id $x WM_NAME 2>/dev/null | grep -q 'LibreOffice' && echo $x && break; done); sleep 0.05; i=$((i+1)); done
echo "$(ts) XID $w (first LibreOffice-named window seen by xdotool)" >> "$out"
declare -A seen
deadline=$(( $(date +%s) + 90 ))
while [ $(date +%s) -lt $deadline ]; do
  for p in _GTK_UNIQUE_BUS_NAME _GTK_MENUBAR_OBJECT_PATH _GTK_WINDOW_OBJECT_PATH _GTK_APPLICATION_OBJECT_PATH _GTK_APP_MENU_OBJECT_PATH; do
    if [ -z "${seen[$p]:-}" ]; then
      v=$(xprop -id "$w" "$p" 2>/dev/null | grep -v 'not found' | cut -d= -f2-)
      if [ -n "$v" ]; then seen[$p]=1; echo "$(ts) PROP $p =$v" >> "$out"; fi
    fi
  done
  if [ -z "${seen[MAPPED]:-}" ] && xdotool search --onlyvisible --name "LibreOffice Writer" 2>/dev/null | grep -q "^$w\$"; then seen[MAPPED]=1; echo "$(ts) MAPPED (visible to xdotool)" >> "$out"; fi
  [ -n "${seen[_GTK_MENUBAR_OBJECT_PATH]:-}" ] && [ -n "${seen[MAPPED]:-}" ] && [ -n "${seen[_GTK_UNIQUE_BUS_NAME]:-}" ] && break
  sleep 0.05
done
sleep 8
xdotool windowactivate --sync "$w" 2>/dev/null; sleep 2
h=$(gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud.StartQuery "Сохранить" 5 2>/dev/null | grep -c "(Файл)")
echo "$(ts) HUD answered=$h" >> "$out"
kill $mon 2>/dev/null
echo "$(ts) END" >> "$out"
