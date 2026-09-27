#!/bin/bash
# UNITY-20260927-005 (agent A): what unity-settings-daemon's package puts into a
# Unity session, and what actually runs. For each .desktop/.service/polkit file
# the package ships: the program it names, whether that program exists,
# whether systemd started it, its processes, and its journal lines this boot.
. ~/envt.sh
V=$(dpkg-query -W -f '${Version}' unity-settings-daemon)
echo "== unity-settings-daemon $V, boot $(uptime -s), XDG_CURRENT_DESKTOP of compiz: $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep ^XDG_CURRENT_DESKTOP)"
for f in $(dpkg -L unity-settings-daemon | grep -E '\.desktop$|\.service$|\.policy$|\.target$|/autostart/'); do
  [ -f "$f" ] || continue
  echo "-- $f"
  case $f in
    *.desktop) grep -E '^(Exec|OnlyShowIn|NotShowIn|X-systemd-skip|AutostartCondition|X-GNOME-AutoRestart|NoDisplay|Hidden)=' "$f" | sed 's/^/   /'
               p=$(grep -m1 '^Exec=' "$f" | cut -d= -f2- | awk '{print $1}')
               [ -n "$p" ] && { [ -x "$p" ] && echo "   program exists: $p" || echo "   PROGRAM MISSING: $p"; }
               u="app-$(systemd-escape "$(basename "$f" .desktop)")@autostart.service"
               echo "   $u: $(systemctl --user show -p LoadState,ActiveState,SubState,Result,ExecMainStatus --value "$u" | tr '\n' ' ')";;
    *.service) grep -E '^(ExecStart|PartOf|After|Requisite|BindsTo)=' "$f" | sed 's/^/   /';;
    *.policy)  grep -oE 'exec.path">[^<]+' "$f" | sed 's/exec.path">/   exec.path /' | while read a b; do [ -x "$b" ] && echo "   $b (exists)" || echo "   $b (MISSING)"; done;;
  esac
done
echo "== processes"; ps -eo pid,ppid,unit:45,args --no-headers | grep -E '[u]nity-settings-daemon|[u]nity-fallback-mount|[u]sd-|[l]ocaleexec' | cut -c1-200
echo "== journal (this boot, user) for these"; journalctl --user -b --no-pager -o short-monotonic | grep -E 'unity-settings|fallback-mount|usd-|IdleMonitor|autostart' | grep -viE 'Started|Starting' | tail -30
