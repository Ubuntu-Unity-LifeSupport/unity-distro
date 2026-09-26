#!/bin/bash
# cinnamon-session #202 conditions under Unity: session clients with a D-Bus
# connection die by SIGTRAP (Obsidian/Chromium int3 in the report), SIGSEGV,
# SIGABRT. After each: is the session still there, and did cinnamon-session log
# a lost name or the g_variant_unref warning? Agent A.
. ~/envt.sh; T0=$(date +%T)
cs=$(pgrep -u mike -x cinnamon-sessio); cz=$(pgrep -u mike -x compiz)
for sig in TRAP SEGV ABRT; do
  for app in gnome-text-editor gnome-characters nemo; do
    (setsid nohup $app >/dev/null 2>&1 &); sleep 5
    p=$(pgrep -u mike -n -x "${app:0:15}"); [ -z "$p" ] && { echo "$sig $app: did not start"; continue; }
    kill -$sig $p; sleep 3
    echo "$sig $app($p): session cinnamon-session=$([ "$(pgrep -u mike -x cinnamon-sessio)" = "$cs" ] && echo same || echo CHANGED) compiz=$([ "$(pgrep -u mike -x compiz)" = "$cz" ] && echo same || echo CHANGED)"
  done
done
echo "journal since $T0: lost-name=$(journalctl --user --since $T0 --no-pager | grep -c 'Lost name on bus') g_variant_unref=$(journalctl --user --since $T0 --no-pager | grep -c g_variant_unref) sm-criticals=$(journalctl --user --since $T0 --no-pager | grep -c 'cinnamon-session.*CRITICAL')"
