#!/bin/bash
# regr.sh TAG - on target2 in the Unity session (as mike over ssh): the UNITY-20261012-003 regression set and an
# application without a menu, each started in the session's environment (taken from compiz) with unity-gtk4-menu's
# debug log on, for 10 s. Prints what the library did: whether the menu was found at realize, and whether a late look,
# a wait or a late fill happened (none should, except "waits" for an application without a menu), plus the window's
# _GTK_MENUBAR_OBJECT_PATH. The keys are tested separately (trial.sh of UNITY-20261012-003).
set -u
tag=$1
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
echo "== $tag at $(date -u +%FT%TZ), boot $(uptime -s), $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0)"
for a in gnome-text-editor gnome-calculator "python3 $HOME/b1203/mnemo.py" gnome-tour; do
  n=$(basename "${a##* }" .py); log=/tmp/ugm-$tag-$n.log; rm -f "$log"
  pkill -x "$(basename "${a%% *}" | cut -c1-15)" 2>/dev/null; sleep 1
  env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG="$log" $a > /dev/null 2>&1 & p=$!
  sleep 10
  w=$(xdotool search --onlyvisible --pid "$p" 2>/dev/null | tail -1)
  echo "-- $a (pid $p, window ${w:-none})"
  echo "  $(xprop -id "$w" _GTK_MENUBAR_OBJECT_PATH 2>&1 | cut -c1-90)"
  for k in "menubar filled," "empty menubar set" "waits for a menu" "late look" "filled late" "stopped waiting"; do
    printf '  %-20s %s\n' "$k:" "$(grep -c "$k" "$log" 2>/dev/null)"
  done
  grep -vE 'hooked|GTK4 (found|is not)' "$log" 2>/dev/null | head -4 | sed 's/^/    log: /'
  kill "$p" 2>/dev/null; sleep 1
done
