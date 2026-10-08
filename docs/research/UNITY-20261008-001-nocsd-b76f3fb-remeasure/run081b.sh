#!/bin/bash
# run081b.sh - UNITY-20261008-001, second part: the hidden-button count (debug builds with dbgpatch.py, the
# 44-application audit, then the DROPPED-CUSTOM lines per application from the apps' stderr), for our series
# and for b76f3fb. At the end the packaged libgtk-nocsd.so.0 is put back.
set -u
PKG=~/b081/libgtk-nocsd.so.0.pkg
APPS="yelp loupe kgx file-roller baobab gnome-clocks gnome-system-monitor papers gnome-calculator gnome-logs simple-scan gnome-text-editor nautilus gnome-contacts gnome-characters gnome-weather gnome-tweaks gnome-music gnome-maps gnome-calendar secrets fragments amberol showtime epiphany gnome-tour d-spy celluloid shortwave foliate apostrophe gnome-chess gnome-mines quadrapassel gnome-2048 gnome-sudoku gnome-robots gnome-nibbles swell-foop lightsoff evince dialect deja-dup gnome-firmware"
clean() { for a in $APPS; do pkill -x "${a:0:15}" 2>/dev/null; done; sleep 2; for a in $APPS; do pkill -9 -x "${a:0:15}" 2>/dev/null; done; sleep 1; }
for v in 60ec176:S:GTK_NOCSD_GLOBAL_MENU=1 b76f3fb:U:GTK_NOCSD_MENU=1; do
  IFS=: read c n e <<<"$v"
  d=~/b081/nocsd-$c-dbg
  rm -rf "${d:?}"; cp -a ~/b081/nocsd-$c "$d"
  python3 ~/b081/dbgpatch.py "$d/Source/GTK-NoCSD.c" && (cd "$d" && make clean >/dev/null && make > ../build-$c-dbg.log 2>&1)
  rc=$?
  echo "## $(date -u +%FT%TZ) debug build $c: rc=$rc warnings=$(grep -c warning: ~/b081/build-$c-dbg.log)"
  [ $rc -eq 0 ] && [ -f "$d/libgtk-nocsd.so.0" ] || { echo "## debug build $c failed, stop"; exit 1; }
  clean; rm -f /tmp/b-breadth-*.out
  bash ~/b/variant.sh "$n-dbg" "$d/libgtk-nocsd.so.0" "$e"
  grep -H DROPPED-CUSTOM /tmp/b-breadth-*.out > ~/b/live/dropped-$n.txt 2>/dev/null
  echo "## $n dropped custom items in: $(cut -d: -f1 ~/b/live/dropped-$n.txt | sort -u | sed 's#/tmp/b-breadth-##; s#\.out##' | tr '\n' ' ')"
done
clean
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
sudo -n cp "$PKG" $T.new && sudo -n mv $T.new $T
echo "## $(date -u +%FT%TZ) packaged library restored: $(sha256sum $T | cut -c1-16); dpkg -V: $(dpkg -V libgtk-nocsd0 | wc -l) lines"
