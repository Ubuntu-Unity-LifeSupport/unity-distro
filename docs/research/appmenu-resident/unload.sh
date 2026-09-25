#!/bin/bash
# unload.sh MODE - MODE=setting: appmenu module only via the gtk-modules XSETTING;
# MODE=env: module via GTK_MODULES (as in the Unity session). After 6 s the
# setting drops the module; the app keeps creating menu bars.
M=${MODULE:-/usr/lib/x86_64-linux-gnu/gtk-3.0/modules/libappmenu-gtk-module.so}
Xvfb :9 -screen 0 800x600x24 >/dev/null 2>&1 & X=$!; sleep 2
export DISPLAY=:9 UBUNTU_MENUPROXY=1 NO_AT_BRIDGE=1
unset LD_PRELOAD GTK_MODULES
C=/tmp/b-xsettingsd.conf
dbus-run-session -- bash -c "
  echo 'Gtk/Modules \"$M\"' > $C
  xsettingsd -c $C >/dev/null 2>&1 & XS=\$!
  sleep 1
  if [ $1 = env ]; then export GTK_MODULES=$M; fi
  python3 ~/b/menuapp.py 18 > /tmp/b-menuapp.out 2>&1 & A=\$!
  sleep 6
  echo 'Gtk/Modules \"\"' > $C; kill -HUP \$XS
  echo '--- setting changed (module dropped from gtk-modules)' >> /tmp/b-menuapp.out
  wait \$A; echo \"app exit status \$?\" >> /tmp/b-menuapp.out
  kill \$XS"
kill $X
cat /tmp/b-menuapp.out | grep -v Gtk-WARNING
