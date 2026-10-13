#!/bin/bash
# survey.sh - UNITY-20261009-004, the reach: the application set of UNITY-20261008-001 (43 GTK4 apps, the 10 GTK3
# apps) plus gnome-terminal, on our packaged stack as a user has it (gtk-nocsd 4.8-1+unity3, libunity-gtk4-menu0 0.9
# installed explicitly, the session's own LD_PRELOAD). Installs the applications, starts each one alone, runs
# survey.py on it, kills it. Output: ~/b0309/survey.jsonl (one JSON line per menu item, one summary line per app).
set -u
B=~/b0309
export DISPLAY=:0
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
# binary:package
APPS="yelp:yelp loupe:loupe kgx:gnome-console file-roller:file-roller baobab:baobab gnome-clocks:gnome-clocks
 gnome-system-monitor:gnome-system-monitor papers:papers gnome-calculator:gnome-calculator gnome-logs:gnome-logs
 simple-scan:simple-scan gnome-text-editor:gnome-text-editor nautilus:nautilus gnome-contacts:gnome-contacts
 gnome-characters:gnome-characters gnome-weather:gnome-weather gnome-tweaks:gnome-tweaks gnome-music:gnome-music
 gnome-maps:gnome-maps gnome-calendar:gnome-calendar secrets:secrets fragments:fragments amberol:amberol
 showtime:showtime epiphany:epiphany-browser gnome-tour:gnome-tour d-spy:d-spy celluloid:celluloid
 shortwave:shortwave foliate:foliate apostrophe:apostrophe gnome-chess:gnome-chess gnome-mines:gnome-mines
 quadrapassel:quadrapassel gnome-2048:gnome-2048 gnome-sudoku:gnome-sudoku gnome-robots:gnome-robots
 gnome-nibbles:gnome-nibbles swell-foop:swell-foop lightsoff:lightsoff evince:evince dialect:dialect
 deja-dup:deja-dup gnome-firmware:gnome-firmware
 gnome-disks:gnome-disk-utility gnome-connections:gnome-connections dconf-editor:dconf-editor seahorse:seahorse
 gnome-taquin:gnome-taquin gnome-tetravex:gnome-tetravex four-in-a-row:four-in-a-row five-or-more:five-or-more
 hitori:hitori gnome-klotski:gnome-klotski gnome-terminal:gnome-terminal"
case ${1:-run} in
install)
  touch ~/.dirty
  pk=""; for a in $APPS; do pk="$pk ${a#*:}"; done
  pk="$pk libunity-gtk4-menu0"
  for p in $pk; do
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $p > /tmp/i-$p.log 2>&1 || echo "install FAILED: $p"
  done
  echo "installed: $(for p in $pk; do dpkg-query -W -f='${Status}\n' $p 2>/dev/null; done | grep -c 'ok installed') of $(echo $pk | wc -w)" ;;
run)
  : > $B/survey.jsonl
  for a in $APPS; do
    bin=${a%%:*}
    command -v $bin > /dev/null || { echo "{\"app\": \"$bin\", \"error\": \"not installed\"}" >> $B/survey.jsonl; continue; }
    pkill -x "${bin:0:15}"; sleep 1
    (env -i "${envs[@]}" setsid sh -c "$bin" > /tmp/sv-$bin.out 2>&1 < /dev/null &)
    sleep 12
    pid=$(pgrep -nx "${bin:0:15}")
    [ "$bin" = gnome-terminal ] && pid=$(pgrep -nx gnome-terminal-)
    if [ -z "$pid" ]; then echo "{\"app\": \"$bin\", \"error\": \"no process\"}" >> $B/survey.jsonl; continue; fi
    w=$(xdotool search --onlyvisible --pid $pid | tail -1); [ -n "$w" ] && xdotool windowactivate --sync $w 2>/dev/null
    sleep 2
    python3 $B/survey.py $bin $pid >> $B/survey.jsonl 2>> $B/survey.err
    pkill -x "${bin:0:15}"; [ "$bin" = gnome-terminal ] && pkill -x gnome-terminal-
    sleep 2
  done
  echo "done: $(grep -c '"summary": true' $B/survey.jsonl) apps surveyed, $(grep -c '"action"' $B/survey.jsonl) items" ;;
esac
