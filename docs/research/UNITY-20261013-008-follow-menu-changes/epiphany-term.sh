#!/bin/bash
# epiphany-term.sh - on target2 in the Unity session: does epiphany abort when it gets SIGTERM, and does
# unity-gtk4-menu change that? Three runs each: the session's environment with its LD_PRELOAD (both libraries), and
# the same environment with only gtk-nocsd preloaded, and with no preload at all (FORMS selects). Each run: epiphany started, 15 s, SIGTERM, its exit status
# (134 = SIGABRT) and the last lines of its stderr. Every epiphany is ended before a run, so each run starts the
# primary instance itself instead of handing off to one left running.
set -u
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
L=/usr/lib/x86_64-linux-gnu
for form in ${FORMS:-session nocsd-only none}; do
  for r in 1 2 3; do
    case $form in
      session)    pre=$(tr '\0' '\n' < /proc/$sp/environ | sed -n 's/^LD_PRELOAD=//p') ;;
      nocsd-only) pre=$L/libgtk-nocsd.so.0 ;;
      none)       pre= ;;
    esac
    pkill -x epiphany; for i in $(seq 30); do pgrep -x epiphany > /dev/null || break; sleep 1; done
    left=$(pgrep -x epiphany | xargs)
    env -i "${envs[@]}" LD_PRELOAD="$pre" epiphany > /tmp/epi-$form-$r.err 2>&1 & p=$!
    sleep 2; mine=$(pgrep -x epiphany | xargs)
    sleep 15
    kill -TERM "$p"; wait "$p"; rc=$?
    echo "  $form run $r: before the start ${left:-no epiphany}; after it: $mine; exit status $rc$([ $rc = 134 ] && echo ' (SIGABRT)')"
    grep -vE '^$' /tmp/epi-$form-$r.err | tail -3 | cut -c1-170 | sed 's/^/      /'
    sleep 2
  done
done
