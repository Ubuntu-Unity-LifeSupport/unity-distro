#!/bin/sh
# UNITY-20260927-008: the scenarios of research/compiz-restart on the
# installed packages, as mike over ssh. Usage: run-all.sh OUTDIR
#  1. 2x2 workspaces (the key the Settings checkbox writes), one xterm per
#     viewport + a gnome-terminal on (1280,0) (vpsetup.sh)
#  2. five `killall -1 compiz`, 30 s apart: window positions after each
#     (vpdump.sh), compiz pid, then a screenshot of each viewport
#  3. `systemctl --user restart unity7.service`: positions, screenshots
#  4. gtk-nocsd's crash handler: a GTK3 window that segfaults (nocsdcrash.sh)
#  and after each step: segfaults / core dumps / g_hash_table criticals in
#  the journal, /var/crash.
set -u
. ~/envt.sh
D=${1:?outdir}; mkdir -p "$D"
T0=$(date '+%F %T')
crashes() { echo "journal since $T0: segfault|general protection|dumped core|g_hash_table: $(journalctl --since "$T0" --no-pager -o short-iso | grep -c -E 'segfault|general protection|dumped core|core-dump|g_hash_table')"; echo "/var/crash: $(ls /var/crash | tr '\n' ' ')"; }
pos() { ~/vpdump.sh 2>/dev/null | grep -oE 'abs=[0-9-]+,[0-9-]+ rel=[^ ]+ "(vp|gt)-[^"]*"' | awk '{gsub(/"/,"",$3); print $3"@"substr($1,5)}' | sort | tr '\n' ' '; }
shots() { tag=$1; for vp in "0 0" "1280 0" "0 800" "1280 800"; do set -- $vp; xdotool set_desktop_viewport $1 $2; sleep 2; gnome-screenshot -f "$D/$tag-vp-$1-$2.png" 2>/dev/null; done; xdotool set_desktop_viewport 0 0; sleep 1; }
# wait until compiz manages windows, then let the session settle
i=0; until xprop -root _NET_CLIENT_LIST 2>/dev/null | grep -q '#' || [ $i -ge 120 ]; do sleep 1; i=$((i+1)); done
sleep 30
{
echo "packages: $(dpkg-query -W -f='${Package}=${Version} ' unity compiz-core libgtk-nocsd0 cinnamon-session nux-tools 2>/dev/null)"
gsettings set org.compiz.core:/org/compiz/profiles/unity/plugins/core/ hsize 2
gsettings set org.compiz.core:/org/compiz/profiles/unity/plugins/core/ vsize 2
sleep 3
echo "geometry: $(xprop -root _NET_DESKTOP_GEOMETRY | sed 's/.*= //')"
~/vpsetup.sh; sleep 3
# the lower-row windows at y 1000 (absolute), as in research/compiz-restart
xdotool set_desktop_viewport 0 0; sleep 2
xdotool windowmove "$(xdotool search --name '^vp-0-800$' | head -1)" 200 1000
xdotool windowmove "$(xdotool search --name '^vp-1280-800$' | head -1)" 1480 1000
sleep 2
echo "before:     compiz=$(pgrep -x compiz) $(pos)"
for i in 1 2 3 4 5; do
  killall -1 compiz; sleep 30
  echo "sighup $i:   compiz=$(pgrep -x compiz) $(pos)"
done
crashes
shots after-5-sighup
systemctl --user restart unity7.service; sleep 35
echo "unity7 restart: compiz=$(pgrep -x compiz) $(pos)"
crashes
shots after-unity7-restart
echo "--- gtk-nocsd crash handler"
~/nocsdcrash.sh 2>&1
crashes
} 2>&1 | tee "$D/log.txt"
