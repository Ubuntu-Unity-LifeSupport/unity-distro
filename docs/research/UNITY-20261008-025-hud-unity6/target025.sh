#!/bin/bash
# target025.sh - hud +unity6 target check on target2 (run as mike over ssh, in the Unity session); the same steps
# before (+unity5) and after (+unity6).
#   1. versions and the running hud-service
#   2. -025: OpenQueries and deleted mappings; 5 one-off StartQuery clients (exit without CloseQuery); 10 s later;
#      a client StartQuery + CloseQuery that exits inside the 2 s; a client StartQuery + ExecuteQuery of the
#      harmless "Свернуть" item (an integer key from its own suggestions, a window focused) that exits;
#      hud-service still the same process, no coredump
#   3. -017: the B017 window (desktop file only in ~/.local/share/applications); an override of
#      org.gnome.Terminal.desktop in ~/.local/share/applications with Icon=b017-override; Writer's icon; cleanup
#   4. -018: bamfdaemon killed while the bridge runs, then a window opened: its stack id
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
HUD="--dest com.canonical.hud --object-path /com/canonical/hud"
P=$(pgrep -x hud-service | head -1)
# live query objects: every QueryImpl is exported as /com/canonical/hud/query/N until it is destroyed (a legacy
# query whose sender left is no longer in OpenQueries, which lists m_queries, but its object stays)
state() { echo "query-objects $(gdbus introspect --session $HUD/query 2>/dev/null | grep -c 'node [0-9]') OpenQueries $(gdbus call --session $HUD --method org.freedesktop.DBus.Properties.Get com.canonical.hud OpenQueries | grep -o '/com/canonical/hud/query/[0-9]*' | wc -l) deleted-maps $(grep -c '(deleted)$' /proc/$P/maps) pid $(pgrep -x hud-service)"; }
start() { local C=$(pgrep -x compiz); (cat /proc/$C/environ; printf 'setsid\0sh\0-c\0%s\0' "$1") > ~/.t25-args
  xargs -0 -a ~/.t25-args env -i > /dev/null 2>&1 < /dev/null & }
icon() { gdbus call --session $HUD --method com.canonical.hud.StartQuery "$1" 1 | grep -o "^('[^']*', \[('[^']*', '[^']*'" | sed "s/.*, '//; s/'$//"; }
echo "== 1 versions"
dpkg-query -W hud libcolumbus1v5 unity bamfdaemon
echo "hud-service pid $P sha256 $(sha256sum /proc/$P/exe | cut -c1-16) deleted-libs $(grep '(deleted)' /proc/$P/maps | grep -vc ' /tmp/')"
echo "== 2 -025"
start "gnome-mines"; sleep 6; M=$(xdotool search --onlyvisible --name "Мины" | tail -1); xdotool windowactivate --sync $M; sleep 1
echo "start: $(state)"
for i in 1 2 3 4 5; do gdbus call --session $HUD --method com.canonical.hud.StartQuery "свер" 3 > /dev/null; done
echo "after 5 one-off StartQuery clients: $(state)"; sleep 10
echo "10 s later: $(state)"
python3 - <<'EOF'
from gi.repository import Gio, GLib
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'StartQuery',
              GLib.Variant('(si)', ('свер', 3)), None, 0, 5000, None)
bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'CloseQuery',
              GLib.Variant('(v)', (GLib.Variant('s', ''),)), None, 0, 5000, None)
EOF
sleep 4; echo "after a StartQuery + CloseQuery client that exited at once: $(state)"
xdotool windowactivate --sync $M; sleep 1
python3 - <<'EOF'
import time
from gi.repository import Gio, GLib
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
target, suggestions, key = bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'StartQuery',
                                         GLib.Variant('(si)', ('Свернуть', 1)), None, 0, 5000, None).unpack()
name, item = suggestions[0][0], suggestions[0][5]
print("  ExecuteQuery item:", name, type(item).__name__, item)
assert 'Свернуть' in name.replace('<b>', '').replace('</b>', '') and isinstance(item, int)
bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'ExecuteQuery',
              GLib.Variant('(vu)', (GLib.Variant('t', item), int(time.time()))), None, 0, 5000, None)
EOF
sleep 4; echo "after a StartQuery + ExecuteQuery client: $(state)"
echo "coredumps of hud-service this boot: $(coredumpctl list --no-pager --since "$(uptime -s)" hud-service 2>/dev/null | grep -c hud-service)"
xdotool windowclose $(xdotool search --name "Мины" | tail -1) 2>/dev/null; sleep 1
echo "== 3 -017"
D=~/.local/share/applications; mkdir -p $D
printf '[Desktop Entry]\nType=Application\nName=B017 Window\nIcon=utilities-terminal\nExec=python3 %s/b025/b017.py\n' "$HOME" > $D/org.example.B017.desktop
printf '%s\n' 'import gi' "gi.require_version('Gtk', '3.0')" 'from gi.repository import Gtk' \
  "app = Gtk.Application(application_id='org.example.B017')" \
  'def activate(a):' "    w = Gtk.ApplicationWindow(application=a, title='B017 Window')" '    w.set_default_size(300, 200)' \
  '    w.show_all()' "app.connect('activate', activate)" 'app.run(None)' > ~/b025/b017.py
start "python3 $HOME/b025/b017.py"; sleep 8
W=$(xdotool search --onlyvisible --name "B017 Window" | tail -1); xdotool windowactivate --sync $W; sleep 1
echo "B017 window: legacy icon '$(icon "свер")'"
xdotool windowclose $W 2>/dev/null; sleep 1
sed 's/^Icon=.*/Icon=b017-override/' /usr/share/applications/org.gnome.Terminal.desktop > $D/org.gnome.Terminal.desktop
start "gnome-terminal"; sleep 6; T=$(xdotool search --onlyvisible --name "mike@target2" | tail -1); xdotool windowactivate --sync $T; sleep 1
echo "Terminal with a user override (Icon=b017-override): legacy icon '$(icon "Создать окно")'"
xdotool windowclose $T 2>/dev/null; sleep 1
rm -f $D/org.gnome.Terminal.desktop $D/org.example.B017.desktop
start "libreoffice --writer --norestore"; for i in $(seq 60); do xdotool search --onlyvisible --name "LibreOffice Writer" >/dev/null 2>&1 && break; sleep 1; done; sleep 8
d=$(xdotool search --onlyvisible --name "Добро пожаловать" | tail -1); [ -n "$d" ] && { xdotool windowactivate --sync $d; xdotool key Escape; sleep 2; }
X=$(xdotool search --onlyvisible --name "LibreOffice Writer" | tail -1); xdotool windowactivate --sync $X; sleep 1
echo "Writer: legacy icon '$(icon "Сохранить")'"
pkill -x soffice.bin; sleep 2
echo "== 4 -018"
p=$(pgrep -x bamfdaemon); kill $p; sleep 6
start "gnome-terminal"; sleep 8; T=$(xdotool search --onlyvisible --name "mike@target2" | tail -1)
echo "bamfdaemon $p -> $(pgrep -x bamfdaemon), bridge $(pgrep -x window-stack-br); Terminal window $T opened after the restart: $(gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack | grep -o "($T, '[^']*'")"
xdotool windowclose $T 2>/dev/null; sleep 1
echo "end: $(state)"
