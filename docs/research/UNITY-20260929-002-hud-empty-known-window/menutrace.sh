#!/bin/bash
# menutrace.sh OUT - run on target2 in the Unity session. Records on the session bus, with timestamps, the
# order of: the window stack bridge's WindowCreated/FocusedWindowChanged signals, hud-service's org.gtk.Menus
# Start calls and their replies (how many items the menu model had when hud-service subscribed), and the
# application's org.gtk.Menus Changed signals (items added later), around one LibreOffice Writer start,
# then one HUD query. The measurement: did hud-service subscribe (Start) before the model was filled
# (Changed after the Start reply), and did the HUD answer.
set -u
out=${1:?out}
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep 2
echo "# menutrace $(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id) uptime=$(cut -d' ' -f1 /proc/uptime) hud-service pid=$(pgrep -x hud-service)" > "$out"
dbus-monitor --session "interface='org.gtk.Menus'" "interface='com.canonical.Unity.WindowStack'" "interface='com.canonical.hud'" > "$out.raw" 2>&1 &
mon=$!
sleep 1
P=$(pgrep -x compiz)
(cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "libreoffice --writer --norestore") > ~/.ht-args
echo "$(date +%s.%N | cut -c1-14) START libreoffice --writer" >> "$out"
xargs -0 -a ~/.ht-args env -i > ~/app-lo.log 2>&1 < /dev/null &
i=0; while ! xdotool search --onlyvisible --name "LibreOffice Writer" >/dev/null 2>&1 && [ $i -lt 90 ]; do sleep 1; i=$((i+1)); done
sleep 8
w=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1)
echo "$(date +%s.%N | cut -c1-14) XID $w visible; WM_NAME=$(xprop -id $w WM_NAME 2>/dev/null | cut -d= -f2-)" >> "$out"
xprop -id "$w" _GTK_UNIQUE_BUS_NAME _GTK_MENUBAR_OBJECT_PATH 2>/dev/null | sed 's/^/PROP /' >> "$out"
xdotool windowactivate --sync "$w"; sleep 2
h=$(gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud.StartQuery "Сохранить" 5 2>/dev/null | grep -c "(Файл)")
echo "$(date +%s.%N | cut -c1-14) HUD answered=$h" >> "$out"
bus=$(xprop -id "$w" _GTK_UNIQUE_BUS_NAME 2>/dev/null | cut -d'"' -f2); path=$(xprop -id "$w" _GTK_MENUBAR_OBJECT_PATH 2>/dev/null | cut -d'"' -f2)
echo "## the model now (org.gtk.Menus Start group 0 on $bus $path): items in group 0" >> "$out"
gdbus call --session --dest "$bus" --object-path "$path" --method org.gtk.Menus.Start "[0]" 2>&1 | cut -c1-300 >> "$out"
gdbus call --session --dest "$bus" --object-path "$path" --method org.gtk.Menus.End "[0]" >/dev/null 2>&1
sleep 1; kill $mon 2>/dev/null
echo "## window stack" >> "$out"
gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack 2>&1 | cut -c1-400 >> "$out"
echo "## bus trace (dbus-monitor, filtered): WindowCreated / Start calls and replies / Changed signals" >> "$out"
grep -n -E "^(signal|method call|method return|error)|member=|string \"|array \[|uint32 " "$out.raw" | grep -E "time=|member=(WindowCreated|FocusedWindowChanged|Start|Changed|StartQuery|UpdateQuery)|method return|^[0-9]+:   (array|uint32|string)" | cut -c1-200 >> "$out"
echo "## END $(date -u +%FT%TZ)" >> "$out"
