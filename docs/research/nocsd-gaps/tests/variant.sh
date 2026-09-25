#!/bin/bash
# variant.sh NAME LIB [EXTRA_ENV] - install LIB as libgtk-nocsd.so.0 (atomic
# rename, running processes keep their copy), run the 45-application audit
# with EXTRA_ENV added to the session environment
name=$1; lib=$2; extra=$3
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
sudo -n cp "$lib" $T.new && sudo -n mv $T.new $T
sed "s#setsid env -i \"\${e\[@\]}\"#setsid env -i \"\${e[@]}\" $extra#" ~/b/breadth-any.sh > /tmp/breadth-var.sh
APPS="yelp loupe kgx file-roller baobab gnome-clocks gnome-system-monitor papers gnome-calculator gnome-logs simple-scan gnome-text-editor nautilus gnome-contacts gnome-characters gnome-weather gnome-tweaks gnome-music gnome-maps gnome-calendar secrets fragments amberol showtime epiphany gnome-tour d-spy celluloid shortwave foliate apostrophe gnome-chess gnome-mines quadrapassel gnome-2048 gnome-sudoku gnome-robots gnome-nibbles swell-foop lightsoff evince dialect deja-dup gnome-firmware"
bash /tmp/breadth-var.sh $APPS > ~/b/live/var-$name.txt 2>&1
echo "$name: $(grep -c '^=====' ~/b/live/var-$name.txt) apps, menus $(grep -cE '^ +- ' ~/b/live/var-$name.txt) top, NO-MENUBAR $(grep -c NO-MENUBAR ~/b/live/var-$name.txt), NO-GTK-PROPS $(grep -c NO-GTK-PROPS ~/b/live/var-$name.txt), MISSING $(grep -c MISSING ~/b/live/var-$name.txt), crashes $(ls /var/crash | wc -l)"
