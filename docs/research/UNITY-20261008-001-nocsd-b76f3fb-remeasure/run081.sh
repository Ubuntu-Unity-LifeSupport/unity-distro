#!/bin/bash
# run081.sh - UNITY-20261008-001: the 44-application audit of research/nocsd-gaps (variant.sh, breadth-any.sh,
# audit.py, unchanged) for our series on a57e976 (60ec176, variable GTK_NOCSD_GLOBAL_MENU) and the author's
# main b76f3fb (variable GTK_NOCSD_MENU, grouping GTK_NOCSD_MENU_GROUP). Before each variant every audited
# application left running is killed (a leftover Epiphany took over later launches in UNITY-20260927-034).
# At the end the packaged libgtk-nocsd.so.0 is put back. Results in ~/b/live/var-<name>.txt.
set -u
S=~/b081/nocsd-60ec176/libgtk-nocsd.so.0
U=~/b081/nocsd-b76f3fb/libgtk-nocsd.so.0
PKG=~/b081/libgtk-nocsd.so.0.pkg
APPS="yelp loupe kgx file-roller baobab gnome-clocks gnome-system-monitor papers gnome-calculator gnome-logs simple-scan gnome-text-editor nautilus gnome-contacts gnome-characters gnome-weather gnome-tweaks gnome-music gnome-maps gnome-calendar secrets fragments amberol showtime epiphany gnome-tour d-spy celluloid shortwave foliate apostrophe gnome-chess gnome-mines quadrapassel gnome-2048 gnome-sudoku gnome-robots gnome-nibbles swell-foop lightsoff evince dialect deja-dup gnome-firmware"
clean() { for a in $APPS; do pkill -x "${a:0:15}" 2>/dev/null; done; sleep 2; for a in $APPS; do pkill -9 -x "${a:0:15}" 2>/dev/null; done; sleep 1; }
run() { clean; echo "## $(date -u +%FT%TZ) variant $1"; bash ~/b/variant.sh "$1" "$2" "$3"; }
run S-off "$S" ""
run S-on  "$S" "GTK_NOCSD_GLOBAL_MENU=1"
run U-off "$U" ""
run U-oldvar "$U" "GTK_NOCSD_GLOBAL_MENU=1"
run U-on  "$U" "GTK_NOCSD_MENU=1"
run U-g1  "$U" "GTK_NOCSD_MENU=1 GTK_NOCSD_MENU_GROUP=1"
run U-g2  "$U" "GTK_NOCSD_MENU=1 GTK_NOCSD_MENU_GROUP=2"
clean
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
sudo -n cp "$PKG" $T.new && sudo -n mv $T.new $T
echo "## $(date -u +%FT%TZ) packaged library restored: $(sha256sum $T | cut -c1-16); dpkg -V: $(dpkg -V libgtk-nocsd0 | wc -l) lines"
