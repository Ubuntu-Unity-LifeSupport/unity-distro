#!/bin/bash
# hudtarget.sh - UNITY-20261009-003/-004/-005 target check on target2 (as mike over ssh, in the Unity session), the
# same steps for any hud version. The legacy client hudexec.py makes the calls Unity 7 makes.
#   T1 -004: gnome-terminal "Создать окно" (win.new-terminal, target ('window','current')): terminal windows before
#      and after; the org.gtk.Actions Activate calls dbus-monitor sees
#   T2 -004: gnome-terminal "132×43" (win.size-to, target (uint32 132, uint32 43)): the window geometry before/after
#   T3 -004: gnome-calculator "Научный" (win.number-format, target 'scientific'): the action's state before/after
#   T4 -003: a string key and a structure key: hud-service keeps its PID, no new crash report
set -u
B=~/b0309
export DISPLAY=:0
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
start() { (env -i "${envs[@]}" setsid sh -c "$1" > /dev/null 2>&1 < /dev/null &); }
hudpid() { pgrep -x hud-service | head -1; }
terms() { xdotool search --onlyvisible --name "mike@target2" 2>/dev/null | wc -l; }
prop() { xprop -id $1 $2 | sed -n 's/.*= "\(.*\)"/\1/p'; }
echo "== versions"
dpkg-query -W hud libunity-gtk4-menu0 gnome-terminal gnome-calculator 2>&1 | sed 's/^/  /'
p=$(hudpid); echo "  hud-service pid $p sha256 $(sha256sum < /proc/$p/exe | cut -c1-16), installed $(sha256sum < /usr/lib/x86_64-linux-gnu/hud/hud-service | cut -c1-16), deleted maps $(grep -c '(deleted)' /proc/$p/maps)"
crashes0=$(ls /var/crash/*hud-service* 2>/dev/null | wc -l)

echo "== T1 Terminal: Создать окно"
pkill -x gnome-terminal-; sleep 1; start gnome-terminal; sleep 6
w=$(xdotool search --onlyvisible --name "mike@target2" | tail -1); xdotool windowactivate --sync $w; sleep 1
echo "  terminal windows before: $(terms)"
dbus-monitor --session "interface='org.gtk.Actions'" > /tmp/act1.txt 2>&1 & mon=$!; sleep 1
python3 $B/hudexec.py "Создать окно" | sed 's/^/  /'
sleep 4; kill $mon
echo "  terminal windows after: $(terms)"
echo "  Activate calls: $(grep -c 'member=Activate' /tmp/act1.txt)"; grep -A8 'member=Activate' /tmp/act1.txt | grep -E 'string|uint32|variant|struct' | head -6 | sed 's/^/    /'

echo "== T2 Terminal: 132×43"
pkill -x gnome-terminal-; sleep 1; start gnome-terminal; sleep 6
w=$(xdotool search --onlyvisible --name "mike@target2" | tail -1); xdotool windowactivate --sync $w; sleep 1
echo "  geometry before: $(xdotool getwindowgeometry $w | grep Geometry)"
python3 $B/hudexec.py "132×43" | sed 's/^/  /'
sleep 3
echo "  geometry after: $(xdotool getwindowgeometry $w | grep Geometry)"
pkill -x gnome-terminal-

echo "== T3 Calculator: Научный"
pkill -x gnome-calculato; sleep 1; start gnome-calculator; sleep 8
c=$(xdotool search --onlyvisible --name "Калькулятор" | tail -1); xdotool windowactivate --sync $c; sleep 1
cb=$(prop $c _GTK_UNIQUE_BUS_NAME); cw=$(prop $c _GTK_WINDOW_OBJECT_PATH)
state() { gdbus call --session --dest $cb --object-path $cw --method org.gtk.Actions.Describe number-format 2>&1 | grep -o "\[<'[a-z]*'>\]"; }
echo "  number-format before: $(state)"
python3 $B/hudexec.py "Научный" | sed 's/^/  /'
sleep 3
echo "  number-format after: $(state)"
pkill -x gnome-calculato

echo "== T4 bad keys"
start gnome-terminal; sleep 6
w=$(xdotool search --onlyvisible --name "mike@target2" | tail -1); xdotool windowactivate --sync $w; sleep 1
p=$(hudpid)
python3 $B/hudexec.py "Создать окно" --key-string | sed 's/^/  /'; sleep 2
python3 $B/hudexec.py "Создать окно" --key-struct | sed 's/^/  /'; sleep 3
echo "  hud-service before $p, after $(hudpid); crash reports for hud-service before $crashes0, now $(ls /var/crash/*hud-service* 2>/dev/null | wc -l)"
journalctl --user --since "-30 s" --no-pager | grep -E "hud-service.*(invalid item key|no focused window|Not activating)" | tail -3 | sed 's/^/  /'
pkill -x gnome-terminal-
echo "== end: hud-service pid $(hudpid)"
