#!/bin/bash
# runtests.sh TAG [control] - on target2 (as mike over ssh): build tests/latetest.c and run every case of it and of
# tests/latetest-adw.py against the unity-gtk4-menu installed now, each in its own dbus-run-session + xvfb-run, with
# the library preloaded in the session's order (libunity-gtk4-menu, then gtk-nocsd; preloading it alone breaks
# PyGObject imports, a separate finding), UNITY_GTK4_MENU_FORCE=1, G_DEBUG=fatal-criticals, and the library's debug log.
#   control: LATETEST_CONTROL=1 (the control run against the release before, which writes none of the new log lines)
#   alone:   the library preloaded alone, as with the user's gtk-nocsd opt-out (possible since 0.11, UNITY-20261013-013)
# The test sources are in ~/b1204t (copied beforehand). Output: one line per case plus any FAIL lines.
set -u
B=~/b1204t
tag=$1; mode=${2:-}
LIB=/usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0
PRE=$LIB:/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
[ "$mode" = alone ] && PRE=$LIB
ctl=; [ "$mode" = control ] && ctl=LATETEST_CONTROL=1
echo "== $tag at $(date -u +%FT%TZ); $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0); library sha256 $(sha256sum < $LIB | cut -c1-16)${mode:+; $mode}"
cc -o $B/latetest $B/latetest.c $(pkg-config --cflags --libs gtk4 x11) 2> $B/cc.log; echo "  build latetest rc=$? ($(grep -c warning $B/cc.log) warnings)"
pass=0; fail=0
for c in 1 2 3 4 5 7 8 9 11 12 adw6 adw6a; do
  log=/tmp/ugm-$tag-$c.log; rm -f $log
  case $c in
    adw*) cmd="python3 $B/latetest-adw.py ${c#adw}" ;;
    *)    cmd="$B/latetest $c" ;;
  esac
  out=$(timeout 60 dbus-run-session -- xvfb-run -a env G_DEBUG=fatal-criticals UNITY_GTK4_MENU_FORCE=1 \
        UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=$log $ctl LD_PRELOAD=$PRE $cmd 2>&1); rc=$?
  verdict=$(printf '%s\n' "$out" | grep -E '^(PASS|FAIL) case' | tail -1)
  [ $rc -eq 0 ] && pass=$((pass+1)) || fail=$((fail+1))
  echo "  case $c: rc $rc ${verdict:-no verdict line}"
  printf '%s\n' "$out" | grep -E '^FAIL case|CRITICAL|WARNING|ERROR|Error|Segmentation|Traceback' | grep -v -E 'xdg-desktop-portal|cannot open display' | head -6 | sed 's/^/      /'
done
echo "  total: $pass passed, $fail failed"
