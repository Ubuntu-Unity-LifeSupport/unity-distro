#!/bin/bash
# versions.sh - on target2 (as mike over ssh): PyGObject's first import with each published libunity-gtk4-menu
# (the library files extracted from the archive's debs into ~/b1313/v/<version>.so, not installed), preloaded alone,
# alone plus libgmodule, and in the session's order with gtk-nocsd; then upstream gtk-nocsd built from fd4b76a
# (~/b1313/nocsd), preloaded alone, with GTK_NOCSD_MENU=0 and 1.
set -u
L=/usr/lib/x86_64-linux-gnu; N=$L/libgtk-nocsd.so.0; V=~/b1313/v
imp() { LD_PRELOAD=$1 python3 -c "$2" 2>&1 | tail -1; }
G='from gi.repository import GLib; print("ok")'
echo "== $(date -u +%FT%TZ); python3-gi $(dpkg-query -W -f='${Version}' python3-gi), libgtk-nocsd0 $(dpkg-query -W -f='${Version}' libgtk-nocsd0)"
for v in 0.5 0.6 0.8 0.9 0.10; do
  echo "  $v (g_module_symbol exported: $(nm -D --defined-only $V/$v.so | grep -c ' g_module_symbol$')): alone: $(imp $V/$v.so "$G") | +libgmodule: $(imp $V/$v.so:$L/libgmodule-2.0.so.0 "$G") | then gtk-nocsd: $(imp $V/$v.so:$N "$G") | gtk-nocsd first: $(imp $N:$V/$v.so "$G")"
done
U=~/b1313/nocsd/libgtk-nocsd.so.0
for m in 0 1; do
  for c in "$G" 'import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk; print("ok gtk3")' 'import gi; gi.require_version("Gtk","4.0"); from gi.repository import Gtk; print("ok gtk4")'; do
    echo "  upstream gtk-nocsd fd4b76a alone, GTK_NOCSD_MENU=$m: $(GTK_NOCSD_MENU=$m imp $U "$c")"
  done
done
