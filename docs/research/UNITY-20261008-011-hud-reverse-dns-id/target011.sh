#!/bin/bash
# target011.sh - UNITY-20261008-011/-014 target check on target2 (run as mike over ssh, in the Unity session),
# the same steps before (+unity4) and after (+unity5). Needs ~/b011/repro.sh, usage.py, frequent.py and, for
# "writer N" and "bridge-restart", ~/b011/target.sh from the UNITY-20260929-001 card.
#   1. versions: packages, the running bridge and hud-service, mappings "(deleted)" other than /tmp/#... files
#   2. Terminal, Mines, Disks and Writer started: their stack ids and hud-service's Applications
#   3. legacy StartQuery icons: Terminal "Создать окно" (also its results), Writer "Сохранить" (control)
#   4. "Всегда наверху" twice from the HUD in Terminal (the state ends as it began): the usage rows
#   5. Disks' empty HUD: its first results
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
R="bash $HOME/b011/repro.sh"
win() { xdotool search --onlyvisible --name "$1" 2>/dev/null | tail -1; }
echo "== 1 versions"
dpkg-query -W hud unity bamfdaemon libreoffice-writer gnome-terminal
for n in window-stack-br hud-service; do p=$(pgrep -x $n | head -1); echo "$n pid $p sha256 $(sha256sum /proc/$p/exe | cut -c1-16) deleted-non-tmp $(grep '(deleted)' /proc/$p/maps | grep -vc ' /tmp/#')"; done
echo "== 2 windows"
$R open gnome-terminal gnome-mines gnome-disks
$R open "libreoffice --writer --norestore"
for i in $(seq 60); do [ -n "$(win "LibreOffice Writer")" ] && break; sleep 1; done; sleep 8
d=$(win "Совет дня"); [ -n "$d" ] && { xdotool windowactivate --sync $d; xdotool key Escape; sleep 2; }
T=$(win "mike@target2"); M=$(win "Мины"); K=$(win "Диски"); W=$(win "LibreOffice Writer")
echo "Terminal $T, Mines $M, Disks $K, Writer $W"
for w in $T $M $K $W; do echo "  $w: $($R stack | grep -o "($w, '[^']*'")"; done
echo "Applications: $($R apps)"
echo "== 3 legacy icons"
echo "Terminal: $($R icon $T 'Создать окно' | grep '^(' | cut -c1-300)"
echo "Writer:   $($R icon $W 'Сохранить' | grep '^(' | cut -c1-200)"
echo "== 4 Всегда наверху x2 in Terminal"
$R use $T "Всегда наверху" | tail -1
$R use $T "Всегда наверху" | tail -1
echo "== 5 Disks empty HUD"
$R frequent $K
