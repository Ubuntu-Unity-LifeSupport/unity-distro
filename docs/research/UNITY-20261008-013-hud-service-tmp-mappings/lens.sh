#!/bin/bash
# lens.sh K - UNITY-20261008-013 on target2: the applications scope (unity-lens-applications, in unity-scope-loader)
# re-indexes its application menu 5 s after a desktop file changes and frees the old searcher (three Tries).
# Starts the scope over D-Bus if needed, then K times adds or removes a desktop file in ~/.local/share/applications
# and waits 10 s; prints the scope process's deleted mappings before and after each step.
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
scope_pid() { for p in $(pgrep -x unity-scope-loa); do tr '\0' ' ' < /proc/$p/cmdline | grep -q 'applications/applications.scope' && echo $p; done | head -1; }
P=$(scope_pid)
if [ -z "$P" ]; then
  gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
    --method org.freedesktop.DBus.StartServiceByName com.canonical.Unity.Scope.Applications 0 > /dev/null
  for i in $(seq 30); do P=$(scope_pid); [ -n "$P" ] && break; sleep 1; done
  sleep 15
fi
m() { printf '%-28s deleted-maps %4d tmp-maps %4d rss_kB %7d\n' "$1" "$(grep -c '(deleted)$' /proc/$P/maps)" \
  "$(grep '(deleted)$' /proc/$P/maps | grep -c ' /tmp/')" "$(awk '/^VmRSS/{print $2}' /proc/$P/status)"; }
echo "libcolumbus1v5 $(dpkg-query -W -f='${Version}' libcolumbus1v5), unity-scope-loader (applications) pid $P"
echo "libcolumbus mapping: $(grep libcolumbus /proc/$P/maps | awk '{print $6, $7}' | sort -u | tr '\n' ' ')"
m "start"
D=~/.local/share/applications; mkdir -p $D
for i in $(seq "${1:-5}"); do
  F=$D/b013-test.desktop
  if [ -e $F ]; then rm -f $F; what="removed"; else
    printf '[Desktop Entry]\nType=Application\nName=B013 Test %s\nExec=true\n' "$i" > $F; what="added"; fi
  sleep 10; m "re-index $i ($what)"
done
rm -f $D/b013-test.desktop; sleep 10; m "test file removed"
