#!/bin/bash
# freq.sh N APP - start LibreOffice APP (writer|calc) N times (no reboot, the previous instance killed), and
# per start record the document window, the application id the window stack gives it, the application bamf
# gives it now (ApplicationForXid -> DesktopFile), and whether bamf moved the window between applications
# (a ChildRemoved of the window on one application followed by a ChildAdded on another) in a dbus-monitor
# capture of bamf.
set -u
n=$1; app=$2
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
case $app in writer) title="LibreOffice Writer";; calc) title="LibreOffice Calc";; esac
for i in $(seq "$n"); do
  pkill -x soffice.bin; while pgrep -x soffice.bin >/dev/null; do sleep 1; done; sleep 2
  dbus-monitor --session "sender='org.ayatana.bamf'" > /tmp/freq.raw 2>&1 & mon=$!
  sleep 1
  P=$(pgrep -x compiz)
  (cat /proc/$P/environ; printf 'setsid\0sh\0-c\0%s\0' "libreoffice --$app --norestore") > ~/.ht-args
  xargs -0 -a ~/.ht-args env -i > /dev/null 2>&1 < /dev/null &
  j=0; while ! xdotool search --onlyvisible --name "$title" >/dev/null 2>&1 && [ $j -lt 90 ]; do sleep 1; j=$((j+1)); done
  sleep 6
  kill $mon
  w=$(xdotool search --onlyvisible --name "$title" | tail -1)
  stackid=$(gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack | grep -o "($w, '[^']*'" | cut -d"'" -f2)
  bapp=$(gdbus call --session --dest org.ayatana.bamf --object-path /org/ayatana/bamf/matcher --method org.ayatana.bamf.matcher.ApplicationForXid "$w" | cut -d"'" -f2)
  bdesk=$(gdbus call --session --dest org.ayatana.bamf --object-path "$bapp" --method org.ayatana.bamf.application.DesktopFile | cut -d"'" -f2)
  moved=$(grep -A1 "member=ChildRemoved" /tmp/freq.raw | grep -c "window/$w\"")
  echo "$app start $i: window $w stack app id '$stackid' bamf now $(basename "$bdesk" .desktop) child-removed-of-window $moved"
done
pkill -x soffice.bin
