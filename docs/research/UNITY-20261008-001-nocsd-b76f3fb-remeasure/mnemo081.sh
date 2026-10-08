#!/bin/bash
# mnemo081.sh - Alt mnemonics on the Unity panel, our series (S) against b76f3fb (U):
# 1. Pinta: Alt+F with the window focused; does the panel open the File menu? (a new menu window appears)
# 2. GNOME Text Editor: F10 opens the holder; then the item mnemonic of "_Комбинации клавиш" (к): does the
#    shortcuts window open?
# Each step: the list of mapped windows before and after (xdotool), and a screenshot (gnome-screenshot).
set -u
S=~/b081/nocsd-60ec176/libgtk-nocsd.so.0
U=~/b081/nocsd-b76f3fb/libgtk-nocsd.so.0
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export DISPLAY=:0 $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=')
wins() { xdotool search --onlyvisible --name '.' 2>/dev/null | while read w; do echo "$w:$(xdotool getwindowname $w 2>/dev/null)"; done | sort; }
mkdir -p ~/b081/shots
for v in "S:$S:GTK_NOCSD_GLOBAL_MENU=1" "U:$U:GTK_NOCSD_MENU=1"; do
  IFS=: read name lib extra <<<"$v"
  sudo -n cp "$lib" $T.new && sudo -n mv $T.new $T
  # Pinta
  pkill -x Pinta; sleep 1
  env -i "${envs[@]}" $extra DOTNET_ROLL_FORWARD=Major ~/b081/Pinta-3.1.2/build/bin/Pinta > /tmp/pinta.out 2>&1 & p=$!
  sleep 12; w=$(xdotool search --onlyvisible --pid $p | tail -1); xdotool windowactivate --sync $w; sleep 1
  l0=$(wins)
  xdotool key alt+f; sleep 2
  gnome-screenshot -f ~/b081/shots/mnemo-$name-pinta-altf.png 2>/dev/null
  l1=$(wins)
  echo "$name pinta Alt+F: new windows: $(comm -13 <(echo "$l0") <(echo "$l1") | tr '\n' ' ')"
  xdotool key Escape; sleep 1; kill $p; sleep 2
  # Text Editor
  pkill -x gnome-text-edit; sleep 1
  env -i "${envs[@]}" $extra gnome-text-editor > /tmp/gte.out 2>&1 & q=$!
  sleep 7; w=$(xdotool search --onlyvisible --pid $q | tail -1); xdotool windowactivate --sync $w; sleep 1
  l0=$(wins)
  xdotool key F10; sleep 2
  gnome-screenshot -f ~/b081/shots/mnemo-$name-gte-f10.png 2>/dev/null
  l1=$(wins)
  xdotool key Cyrillic_ka; sleep 3
  gnome-screenshot -f ~/b081/shots/mnemo-$name-gte-ka.png 2>/dev/null
  l2=$(wins)
  echo "$name text-editor F10: new windows: $(comm -13 <(echo "$l0") <(echo "$l1") | tr '\n' ' ')"
  echo "$name text-editor then к: new windows against before F10: $(comm -13 <(echo "$l0") <(echo "$l2") | tr '\n' ' ')"
  xdotool key Escape; sleep 1; xdotool key Escape; kill $q; sleep 2
done
sudo -n cp ~/b081/libgtk-nocsd.so.0.pkg $T.new && sudo -n mv $T.new $T
echo "packaged library restored: $(sha256sum $T | cut -c1-16)"
