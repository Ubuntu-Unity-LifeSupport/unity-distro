#!/bin/bash
# run081g3.sh - UNITY-20261008-001, GTK3: the audit of research/nocsd-gaps (breadth-any.sh, audit.py) on the
# ten GTK3 applications with a menu button of research/nocsd-reply2 (breadth-gtk3.txt), for our series and
# b76f3fb. The session's GTK_MODULES (appmenu-gtk-module) stay as they are; audit.py reads only the _GTK_*
# window properties and the org.gtk.Menus export. Results in ~/b/live/g3-<name>.txt.
set -u
S=~/b081/nocsd-60ec176/libgtk-nocsd.so.0
U=~/b081/nocsd-b76f3fb/libgtk-nocsd.so.0
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
APPS="gnome-disks gnome-connections gnome-taquin gnome-tetravex four-in-a-row five-or-more hitori gnome-klotski dconf-editor seahorse"
clean() { for a in $APPS; do pkill -x "${a:0:15}" 2>/dev/null; done; sleep 2; for a in $APPS; do pkill -9 -x "${a:0:15}" 2>/dev/null; done; sleep 1; }
for v in "S-on:$S:GTK_NOCSD_GLOBAL_MENU=1" "U-off:$U:" "U-on:$U:GTK_NOCSD_MENU=1" "U-g2:$U:GTK_NOCSD_MENU=1 GTK_NOCSD_MENU_GROUP=2"; do
  IFS=: read name lib extra <<<"$v"
  clean
  sudo -n cp "$lib" $T.new && sudo -n mv $T.new $T
  sed "s#setsid env -i \"\${e\[@\]}\"#setsid env -i \"\${e[@]}\" $extra#" ~/b/breadth-any.sh > /tmp/breadth-g3.sh
  echo "## $(date -u +%FT%TZ) GTK3 variant $name"
  PATH=$PATH:/usr/games bash /tmp/breadth-g3.sh $APPS > ~/b/live/g3-$name.txt 2>&1
done
clean
sudo -n cp ~/b081/libgtk-nocsd.so.0.pkg $T.new && sudo -n mv $T.new $T
echo "## $(date -u +%FT%TZ) packaged library restored: $(sha256sum $T | cut -c1-16)"
