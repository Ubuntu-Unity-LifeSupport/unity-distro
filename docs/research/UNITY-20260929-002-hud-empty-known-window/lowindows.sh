#!/bin/sh
# lowindows.sh - run on target2 in the Unity session while LibreOffice is up: list every LibreOffice
# top-level X window with its name, type, transient parent and state, the X focus, and the window
# stack bridge's view (xid, app id, focused). Tells which window the HUD query is served for.
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
echo "== $(date -u +%FT%TZ) X focus: $(xdotool getwindowfocus 2>/dev/null) active: $(xdotool getactivewindow 2>/dev/null)"
for w in $(xdotool search --class libreoffice 2>/dev/null; xdotool search --class soffice 2>/dev/null); do
    name=$(xprop -id "$w" WM_NAME 2>/dev/null | cut -d= -f2-)
    [ -z "$name" ] && continue
    echo "-- xid $w ($(printf '0x%x' "$w")) name=$name"
    xprop -id "$w" WM_CLASS _NET_WM_WINDOW_TYPE WM_TRANSIENT_FOR _NET_WM_STATE _NET_WM_PID 2>/dev/null | sed 's/^/   /'
    echo "   visible=$(xdotool search --onlyvisible --class libreoffice 2>/dev/null | grep -c "^$w\$") gtk_bus=$(xprop -id "$w" _GTK_UNIQUE_BUS_NAME 2>/dev/null | cut -d= -f2-) menubar=$(xprop -id "$w" _GTK_MENUBAR_OBJECT_PATH 2>/dev/null | cut -d= -f2-)"
done
echo "== window stack (xid, app id, focused, stage)"
gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack 2>&1 | cut -c1-600
echo "== HUD query for the focused window"
gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud.StartQuery "Сохранить" 5 2>/dev/null | grep -o "(Файл)" | wc -l
