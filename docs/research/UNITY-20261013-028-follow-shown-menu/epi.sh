#!/bin/bash
# epi.sh [RUNS [DELAY]] - on target2 in the Unity session (as mike over ssh): UNITY-20261013-029's check (029t.sh) on the live
# stack, with unity-gtk4-menu's debug log: epiphany with the default-browser question open, SIGTERM after 15 s, the
# session's preload order (/usr/$LIB/libunity-gtk4-menu.so.0:/usr/$LIB/libgtk-nocsd.so.0, without the test session's
# own libm). Per run: the exit status (134 = SIGABRT), epiphany's ERROR/CRITICAL lines, and every library log line
# after the fill (relooks, switches, orphans, stand-ins moved, the end of following), so an abort can be set against
# what the library did. Crash files are counted, not copied.
# The question shows only when epiphany is not the default http handler: on a clean target2 it is the only browser,
# so the handler was set to another installed application first (gio mime x-scheme-handler/http{,s}
# gnome-disk-image-writer.desktop); the first 10 runs of logs/18, without the question, are kept there and do not count.
set -u
runs=${1:-10}; delay=${2:-15} # seconds from the start to SIGTERM
sp=$(pgrep -x compiz | head -1)
mapfile -t envs < <(tr '\0' '\n' < /proc/$sp/environ | grep -v -E '^(UNITY_GTK4_MENU_[A-Z]+|LD_PRELOAD)=')
export $(printf '%s\n' "${envs[@]}" | grep -E '^(DISPLAY|XAUTHORITY)=')
PRE='/usr/$LIB/libunity-gtk4-menu.so.0:/usr/$LIB/libgtk-nocsd.so.0'
echo "== epi at $(date -u +%FT%TZ), boot $(uptime -s), SIGTERM after ${delay} s; $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}, ' libunity-gtk4-menu0)$(dpkg-query -W -f='libgtk-nocsd0 ${Version}, ' libgtk-nocsd0)$(dpkg-query -W -f='epiphany-browser ${Version}' epiphany-browser)"
echo "  ask-for-default: $(env -i "${envs[@]}" gsettings get org.gnome.Epiphany ask-for-default 2>&1); http handler: $(env -i "${envs[@]}" gio mime x-scheme-handler/http 2>&1 | head -1)"
c0=$(ls /var/crash 2>/dev/null | grep -c epiphany)
ab=0
for r in $(seq 1 $runs); do
  pkill -x epiphany; for i in $(seq 30); do pgrep -x epiphany > /dev/null || break; sleep 1; done
  log=/tmp/epi-dbg-$r.log; rm -f $log
  env -i "${envs[@]}" LD_PRELOAD="$PRE" UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=$log epiphany > /tmp/epi-$r.err 2>&1 & p=$!
  sleep $delay
  wins=$(for w in $(xdotool search --all --pid $p --name '.*' 2>/dev/null); do xdotool getwindowname $w 2>/dev/null; done | grep -v '^$' | tr '\n' '|')
  kill -TERM $p; t=$(date -u +%T.%3N); wait $p; rc=$?
  [ $rc = 134 ] && ab=$((ab + 1))
  echo "run $r: SIGTERM at $t; windows: $wins; exit $rc$([ $rc = 134 ] && echo ' (SIGABRT)')"
  grep -E "ERROR|CRITICAL|assertion" /tmp/epi-$r.err | head -3 | cut -c1-200 | sed 's/^/    epiphany: /'
  sed -E 's/^\[unity-gtk4-menu [0-9]+\] //' $log | sed -n '/menubar filled/,$p' | grep -v -E '^(candidate [0-9]|chose candidate)' | head -20 | sed 's/^/    lib: /'
done
echo "== $ab of $runs aborted; new epiphany crash files: $(( $(ls /var/crash 2>/dev/null | grep -c epiphany) - c0 ))"
