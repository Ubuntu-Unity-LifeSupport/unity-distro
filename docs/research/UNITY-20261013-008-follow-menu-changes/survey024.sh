#!/bin/bash
# survey024.sh - UNITY-20261013-024's survey, on target2 in the Unity session (as mike over ssh): does any real GTK 4
# application set a menubar of its own after realize (after unity-gtk4-menu 0.12 set its own), the case
# takeover.py of UNITY-20261013-023 builds? Each application is started in the session's environment with the
# library's debug log for 15 s, then closed. Per application: whether it had a menubar of its own before realize,
# whether ours was filled at realize or late, whether its window waits, and whether "ours is released" (TAKEN after
# ours) appears.
set -u
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
echo "== survey at $(date -u +%FT%TZ); $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0)"
for a in nautilus papers kgx epiphany gnome-contacts gnome-text-editor gnome-characters gnome-calculator \
         gnome-clocks gnome-font-viewer gnome-weather gnome-tweaks gnome-tour; do
  command -v "$a" > /dev/null || { echo "  $a: not installed"; continue; }
  log=/tmp/s024-$a.log; rm -f "$log"
  env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG="$log" "$a" > /dev/null 2>&1 & p=$!
  sleep 15
  c() { grep -c "$1" "$log" 2>/dev/null; }
  printf '  %-18s own-before-realize %s | filled %s | filled-late %s | waits %s | ours-released %s\n' "$a" \
    "$(c 'already has a menubar')" "$(c 'menubar filled,')" "$(c 'filled late')" "$(c 'waits for a menu')" "$(c 'ours is released')"
  kill "$p" 2>/dev/null; sleep 1; kill -9 "$p" 2>/dev/null; true
done
