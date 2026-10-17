#!/bin/bash
# runtests.sh TAG LIB [CASES...] - on target2 (as mike over ssh): run latetest cases against the library LIB (a test
# build in ~/b028t, or the installed /usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0), each in its own
# dbus-run-session + xvfb-run, preloaded in the session's order (LIB, then gtk-nocsd), with UNITY_GTK4_MENU_FORCE=1,
# G_DEBUG=fatal-criticals and the library's debug log. Cases 1f and 3f are 1 and 3 with gtk-shell-shows-menubar
# FALSE; adw6 and adw6a are tests/latetest-adw.py's. LATETEST_CONTROL=1 in the environment is passed on (the
# control run against 0.13). VALGRIND=1 runs each case under valgrind (memcheck, errors counted).
# Output: one line per case, its FAIL lines, and on a failure the library's log of the case.
set -u
B=~/b028t
tag=$1; LIB=$2; shift 2
cases=${*:-1 1f 2 3 3f 4 5 7 8 9 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 adw6 adw6a}
PRE=$LIB:/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
ctl=; [ -n "${LATETEST_CONTROL:-}" ] && ctl=LATETEST_CONTROL=1
vg=; [ -n "${VALGRIND:-}" ] && vg="valgrind -q --error-exitcode=99 --leak-check=no"
echo "== $tag at $(date -u +%FT%TZ); library $LIB sha256 $(sha256sum < $LIB | cut -c1-16)${ctl:+; control}${vg:+; valgrind}"
pass=0; fail=0
for c in $cases; do
  log=/tmp/ugm-$tag-$c.log; rm -f $log
  case $c in
    adw*) cmd="python3 $B/latetest-adw.py ${c#adw}" ;;
    *f)   cmd="env LATETEST_SHELL_MENUBAR=0 $vg $B/latetest ${c%f}" ;;
    *)    cmd="$vg $B/latetest $c" ;;
  esac
  out=$(timeout 180 dbus-run-session -- xvfb-run -a env G_DEBUG=fatal-criticals UNITY_GTK4_MENU_FORCE=1 \
        UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=$log $ctl LD_PRELOAD=$PRE $cmd 2>&1); rc=$?
  verdict=$(printf '%s\n' "$out" | grep -E '^(PASS|FAIL) case' | tail -1)
  if [ $rc = 0 ] && [ -n "$verdict" ] && [ "${verdict#PASS}" != "$verdict" ]; then
    pass=$((pass+1)); echo "  $c: PASS"
  else
    fail=$((fail+1)); echo "  $c: FAIL rc=$rc ${verdict:-no verdict}"
    printf '%s\n' "$out" | grep -E '^FAIL|==[0-9]+==|CRITICAL' | head -15 | sed 's/^/      /'
    sed -E 's/^\[unity-gtk4-menu [0-9]+\] /      lib: /' $log 2>/dev/null | tail -25
  fi
done
echo "== $tag: $pass passed, $fail failed"
