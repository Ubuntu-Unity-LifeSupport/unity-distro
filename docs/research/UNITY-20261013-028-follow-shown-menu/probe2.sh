#!/bin/bash
# probe2.sh STEP - unity-gtk4-menu 0.14 on target2 (as mike over ssh), in the Unity session, applications started in
# the session's environment with the library's debug log; menudump.py (UNITY-20261013-008) reads the export.
#   setup:    gnome-console, nautilus and the survey's applications from the archive
#   console:  T3 - kgx; its tab overview opened (Ctrl+Shift+O) and closed (Escape); the export and a HUD query
#             ("Новое окно", New Window) in each state
#   nautilus [LIB]: T5 - three windows, 20 renames (Nautilus' FileOperations2.RenameURI); rebuilds and window looks
#             ("chose candidate") counted, and the first window's Undo item
#   survey:   T4 - the UNITY-20261013-024 survey of 13 applications, 15 s each: the choice at realize, and every
#             relook and switch
set -u
B=~/b028
sp=$(pgrep -x compiz | head -1)
mapfile -t envs < <(tr '\0' '\n' < /proc/$sp/environ | grep -v -E '^UNITY_GTK4_MENU_[A-Z]+=')
export $(printf '%s\n' "${envs[@]}" | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
liblog() { sed -E 's/^\[unity-gtk4-menu [0-9]+\] /    lib: /' "$1"; }
unlock() {
  loginctl unlock-session "$(loginctl show-user "$USER" -p Display --value)"; xset s off -dpms
  gsettings set org.gnome.desktop.screensaver lock-enabled false; gsettings set org.gnome.desktop.session idle-delay 0
}
dump() { # $1 window
  echo "  window $1 ($(xdotool getwindowname $1))"; python3 $B/menudump.py $1 | sed 's/^/    /'
}
hud() { # $1 query: the HUD's first results
  gdbus call --session --dest com.canonical.hud --object-path /com/canonical/hud \
    --method com.canonical.hud.StartQuery "$1" 5 2>/dev/null | grep -o "'[^']*$1[^']*'" | head -3 | xargs
}
case $1 in
setup)
  echo "== setup at $(date -u +%FT%TZ), boot $(uptime -s)"
  touch ~/.dirty
  until ! sudo fuser /var/lib/dpkg/lock-frontend > /dev/null 2>&1; do sleep 5; done
  P="gnome-console nautilus epiphany-browser gnome-contacts gnome-text-editor gnome-characters gnome-calculator gnome-clocks gnome-font-viewer gnome-weather gnome-tweaks gnome-tour"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/b028-inst2.log 2>&1; echo "  install rc=$?"
  dpkg-query -W libunity-gtk4-menu0 libgtk-nocsd0 $P 2>&1 | sed 's/^/  /'
  ;;
console)
  unlock
  echo "== console at $(date -u +%FT%TZ); $(dpkg-query -W -f='gnome-console ${Version}, libunity-gtk4-menu0 ' gnome-console)$(dpkg-query -W -f='${Version}' libunity-gtk4-menu0)"
  pkill -x kgx; log=/tmp/b028-kgx.log; rm -f $log
  env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=$log setsid kgx > /dev/null 2>&1 < /dev/null &
  sleep 6; w=$(xdotool search --onlyvisible --class '^kgx$|^org.gnome.Console$' | head -1)
  xdotool windowactivate --sync $w; sleep 1
  echo "-- the terminal"; dump $w; echo "  HUD \"Новое окно\": $(hud 'Новое окно')"
  xdotool key ctrl+shift+o; sleep 3
  echo "-- the tab overview opened (Ctrl+Shift+O)"; dump $w; echo "  HUD \"Новое окно\": $(hud 'Новое окно')"
  gnome-screenshot -w -f /tmp/b028-kgx-overview.png 2>/dev/null
  xdotool key Escape; sleep 3
  echo "-- the tab overview closed (Escape)"; dump $w; echo "  HUD \"Новое окно\": $(hud 'Новое окно')"
  echo "  library log:"; liblog $log | grep -v -E 'lib: (GTK4|hooked|empty)'
  pkill -x kgx
  ;;
nautilus)
  # $2: another build of the library to preload in place of the installed one (the 0.13 control)
  if [ -n "${2:-}" ]; then
    mapfile -t envs < <(printf '%s\n' "${envs[@]}" | sed "s|^LD_PRELOAD=.*|LD_PRELOAD=$2:/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0|")
    echo "  control: LD_PRELOAD=$2 ($(sha256sum < $2 | cut -c1-16))"
  fi
  unlock
  echo "== nautilus at $(date -u +%FT%TZ); $(dpkg-query -W -f='nautilus ${Version}, libunity-gtk4-menu0 ' nautilus)$(dpkg-query -W -f='${Version}' libunity-gtk4-menu0)"
  nautilus -q 2> /dev/null; pkill -x nautilus; sleep 1; log=/tmp/b028-naut.log; rm -f $log
  rm -rf -- "${HOME:?}/b028n"; mkdir -p ~/b028n; touch ~/b028n/f0
  env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=$log setsid nautilus --new-window ~/b028n > /dev/null 2>&1 < /dev/null &
  sleep 5
  for k in 2 3; do
    env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=$log nautilus --new-window ~ > /dev/null 2>&1 < /dev/null; sleep 3
  done
  echo "  windows: $(xdotool search --onlyvisible --class '^org.gnome.Nautilus$' | wc -l)"
  looks0=$(grep -c 'chose candidate' $log); rb0=$(grep -c 'menu changed (rebuild' $log)
  w=$(xdotool search --onlyvisible --name '^b028n$' | head -1)
  # renamed through Nautilus' own FileOperations2.RenameURI, which records the undo step as a rename in the window
  # does (typed keys went to Unity's Dash once: F2 with a stuck modifier)
  for i in $(seq 1 20); do
    gdbus call --session -d org.gnome.Nautilus -o /org/gnome/Nautilus/FileOperations2 \
      -m org.gnome.Nautilus.FileOperations2.RenameURI "file://$HOME/b028n/f$((i - 1))" "f$i" '{}' > /dev/null
    sleep 1.5
  done
  echo "  files now: $(ls ~/b028n | xargs)"
  echo "  rebuilds: $(( $(grep -c 'menu changed (rebuild' $log) - rb0 )), window looks: $(( $(grep -c 'chose candidate' $log) - looks0 ))"
  echo "-- the first window's export after the renames"; dump $w | grep -i -E 'Отменить|Undo|Повторить' | head -3
  nautilus -q 2> /dev/null; pkill -x nautilus
  ;;
survey)
  unlock
  echo "== survey at $(date -u +%FT%TZ); $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0)"
  for a in nautilus papers kgx epiphany gnome-contacts gnome-text-editor gnome-characters gnome-calculator \
           gnome-clocks gnome-font-viewer gnome-weather gnome-tweaks gnome-tour; do
    command -v "$a" > /dev/null || { echo "  $a: not installed"; continue; }
    [ "$a" = nautilus ] && { nautilus -q 2> /dev/null; pkill -x nautilus; }
    log=/tmp/b028-s-$a.log; rm -f "$log"
    env -i "${envs[@]}" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG="$log" setsid "$a" > /dev/null 2>&1 < /dev/null & p=$!
    sleep 15
    c() { grep -c "$1" "$log" 2>/dev/null; }
    printf '  %-18s filled %s | late %s | relooks %s | switched %s | kept %s | orphaned %s | adopted %s | released %s\n' "$a" \
      "$(c 'menubar filled,')" "$(c 'filled late')" "$(c '] relook$')" "$(c 'switched to the shown menu')" \
      "$(c 'the menu followed is kept')" "$(c 'no other menu is shown')" "$(c 'owner adopted')" "$(c 'ours is released')"
    kill "$p" 2> /dev/null; pkill -x "$a" 2> /dev/null; sleep 1; pkill -9 -x "$a" 2> /dev/null; true
  done
  ;;
esac
