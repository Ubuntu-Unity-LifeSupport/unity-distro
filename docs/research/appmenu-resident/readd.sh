#!/bin/bash
# readd.sh MODULE SCENARIO - menuapp.py with MODULE only in the gtk-modules
# XSETTING. SCENARIO: keep | drop (removed at 6 s) | readd (removed at 6 s,
# added back at 10 s). Prints the app's exit status.
M=$1; S=$2
D=$((20 + RANDOM % 60)); Xvfb :$D -screen 0 800x600x24 >/dev/null 2>&1 & X=$!; sleep 2
export DISPLAY=:$D UBUNTU_MENUPROXY=1 NO_AT_BRIDGE=1
unset GTK_MODULES
CF=/tmp/amt/xs.conf
dbus-run-session -- bash -c "
  echo 'Gtk/Modules \"$M\"' > $CF
  xsettingsd -c $CF >/dev/null 2>&1 & XS=\$!
  sleep 1
  python3 /tmp/amt/menuapp.py 18 > /tmp/amt/out.txt 2>&1 & A=\$!
  sleep 6
  if [ $S != keep ]; then echo 'Gtk/Modules \"\"' > $CF; kill -HUP \$XS; echo '--- dropped' >> /tmp/amt/out.txt; fi
  sleep 4
  if [ $S = readd ]; then echo 'Gtk/Modules \"$M\"' > $CF; kill -HUP \$XS; echo '--- added back' >> /tmp/amt/out.txt; fi
  wait \$A; echo \"app exit status \$?\" >> /tmp/amt/out.txt
  kill \$XS"
kill $X 2>/dev/null
grep -vE "Gtk-WARNING|^$" /tmp/amt/out.txt | sed -n '1p;/---/p;/tick [3-6] /p;$p' | cut -c1-140
