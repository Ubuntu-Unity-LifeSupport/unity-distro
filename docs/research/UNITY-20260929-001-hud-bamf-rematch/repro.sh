#!/bin/bash
# repro.sh OUT - UNITY-20260929-001 reproduction on target2: one Writer start (as lo7.sh starts it) under a
# dbus-monitor capture of bamf's matcher/application/view signals and the window stack bridge; then the
# window stack (window id, application id, focused), bamf's own answer for the window's application
# (matcher ApplicationForXid, its DesktopFile), and the HUD's legacy StartQuery reply (its first value is
# the target the HUD shows, its suggestions carry the icon). Writes OUT and OUT.raw.
set -u
out=${1:?out}
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep 2
dbus-monitor --session "sender='org.ayatana.bamf'" "interface='com.canonical.Unity.WindowStack'" > "$out.raw" 2>&1 &
mon=$!
sleep 1
P=$(pgrep -x compiz)
(cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "libreoffice --writer --norestore") > ~/.ht-args
echo "# $(date -u +%FT%TZ) START" > "$out"
xargs -0 -a ~/.ht-args env -i > /dev/null 2>&1 < /dev/null &
i=0; while ! xdotool search --onlyvisible --name "LibreOffice Writer" >/dev/null 2>&1 && [ $i -lt 90 ]; do sleep 1; i=$((i+1)); done
sleep 10
w=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1)
xdotool windowactivate --sync "$w"; sleep 2
kill $mon
echo "## Writer window $w ($(xdotool getwindowname $w)); focused: $(xdotool getwindowname $(xdotool getactivewindow))" >> "$out"
echo "## window stack (window id, application id, focused)" >> "$out"
gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack | grep -o "([0-9]*, '[^']*', [a-z]*" | grep -v compiz >> "$out"
app=$(gdbus call --session --dest org.ayatana.bamf --object-path /org/ayatana/bamf/matcher --method org.ayatana.bamf.matcher.ApplicationForXid "$w" | cut -d"'" -f2)
echo "## bamf now: ApplicationForXid $w -> $app, DesktopFile $(gdbus call --session --dest org.ayatana.bamf --object-path "$app" --method org.ayatana.bamf.application.DesktopFile)" >> "$out"
echo "## HUD legacy StartQuery (target, first suggestion)" >> "$out"
gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud.StartQuery "Сохранить" 5 | cut -c1-400 >> "$out"
echo "## bamf and bridge signals around the start (member, argument)" >> "$out"
grep -E "^signal" -A2 "$out.raw" | grep -E "member=(ViewOpened|ViewClosed|ChildAdded|ChildRemoved|WindowAdded|WindowRemoved|WindowCreated|WindowDestroyed|FocusedWindowChanged)|string \"/org/ayatana/bamf/(window|application)/|uint32|string \"[a-z0-9-]*\"" | sed -E 's/.*time=([0-9.]+) sender=(\S+).*path=([^;]+);.*member=(\S+)/\1 \2 \3 \4/' | head -80 >> "$out"
