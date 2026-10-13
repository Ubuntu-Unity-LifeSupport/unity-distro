#!/bin/bash
# repro.sh STEP - hud +unity6 tasks on target2 (run as mike over ssh, in the Unity session).
#   025 [N]   N one-off legacy StartQuery clients (each gdbus call is its own bus connection and exits without
#             CloseQuery): hud-service's deleted mappings and RSS before, after, and 10 s later; then one client
#             that calls StartQuery + CloseQuery and stays (the 2 s timer must close it)
#   017       a GTK window whose desktop file exists only in ~/.local/share/applications
#             (org.example.B017.desktop, Icon=utilities-terminal): its stack id and the legacy StartQuery icon
#   018 [N]   the window-stack-bridge journal of this boot (and of the last N boots if kept): the QtDBus owner warning
#   018-bamf  bamfdaemon killed while the bridge runs: the bridge journal after it restarts
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
HUD="--dest com.canonical.hud --object-path /com/canonical/hud --method com.canonical.hud"
hudmaps() { local P=$(pgrep -x hud-service | head -1)
  echo "deleted-maps $(grep -c '(deleted)$' /proc/$P/maps) rss_kB $(awk '/^VmRSS/{print $2}' /proc/$P/status)"; }
stack() { gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack | grep -o "([0-9]*, '[^']*', [a-z]*" | grep -v compiz | tr '\n' ' '; echo; }
start() { local C=$(pgrep -x compiz); (cat /proc/$C/environ; printf 'setsid\0sh\0-c\0%s\0' "$1") > ~/.r25-args
  xargs -0 -a ~/.r25-args env -i > /dev/null 2>&1 < /dev/null & }
case $1 in
025)
  echo "hud $(dpkg-query -W -f='${Version}' hud), libcolumbus $(dpkg-query -W -f='${Version}' libcolumbus1v5)"
  echo "before: $(hudmaps)"
  for i in $(seq "${2:-5}"); do gdbus call --session $HUD.StartQuery "сохр" 3 > /dev/null; done
  echo "after ${2:-5} one-off StartQuery clients: $(hudmaps)"; sleep 10
  echo "10 s later: $(hudmaps)"
  python3 - <<'EOF'
import time
from gi.repository import Gio, GLib
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
r = bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'StartQuery',
                  GLib.Variant('(si)', ('сохр', 3)), None, 0, 5000, None).unpack()
bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'CloseQuery',
              GLib.Variant('(v)', (GLib.Variant('s', ''),)), None, 0, 5000, None)
time.sleep(5)
EOF
  echo "after a StartQuery + CloseQuery client that stayed 5 s: $(hudmaps)" ;;
017)
  D=~/.local/share/applications; mkdir -p $D
  printf '[Desktop Entry]\nType=Application\nName=B017 Window\nIcon=utilities-terminal\nExec=python3 %s/b025/b017.py\n' "$HOME" > $D/org.example.B017.desktop
  cat > ~/b025/b017.py <<'EOF'
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
app = Gtk.Application(application_id='org.example.B017')
def activate(a):
    w = Gtk.ApplicationWindow(application=a, title='B017 Window')
    w.set_default_size(300, 200)
    w.show_all()
app.connect('activate', activate)
app.run(None)
EOF
  start "python3 $HOME/b025/b017.py"; sleep 8
  W=$(xdotool search --onlyvisible --name "B017 Window" | tail -1); xdotool windowactivate --sync $W; sleep 1
  echo "window $W: $(stack | grep -o "($W, '[^']*'")"
  echo "legacy StartQuery icons: $(gdbus call --session $HUD.StartQuery "свер" 3 | grep -o "'[^']*', '[^']*', '', '', ''" | head -3 | tr '\n' ' ')"
  xdotool windowclose $W 2>/dev/null; sleep 1 ;;
018)
  echo "this boot: $(journalctl --user -b --no-pager 2>/dev/null | grep -c 'had owner')"
  journalctl --user -b --no-pager 2>/dev/null | grep 'had owner' | head -3 ;;
018-bamf)
  B=$(pgrep -x window-stack-br); p=$(pgrep -x bamfdaemon); kill $p; sleep 6
  echo "bamfdaemon $p -> $(pgrep -x bamfdaemon || echo none), bridge $B -> $(pgrep -x window-stack-br)"
  journalctl --user -b --no-pager --since "-20 s" 2>/dev/null | grep -E 'window-stack|had owner' | tail -5 ;;
esac
