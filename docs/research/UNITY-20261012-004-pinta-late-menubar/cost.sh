#!/bin/bash
# cost.sh - on target2 (as mike over ssh): the cost of 0.12's map shim (design item 10).
#   1. maptest.c (an application window without a menu, one GtkMenuButton hidden and shown 10 000 times) under Xvfb,
#      5 runs each with no preload, with 0.11 + gtk-nocsd (no shim; 0.11 extracted to /tmp/u11) and with the installed
#      0.12 + gtk-nocsd; the time per cycle of each run.
#   2. the same 0.12 run once more under bpftrace with uprobes at the static functions' offsets from the dbgsym
#      (build-id 28258fee..., checked against the installed file): calls of shim_menu_button_map and shim_menu_bar_map, and
#      the total time spent in shim_menu_button_map (bpftrace does not resolve the offsets of look() and look_idle(); the looks are counted from the library's debug log instead).
set -u
B=~/b1204t; L=/usr/lib/x86_64-linux-gnu; N=$L/libgtk-nocsd.so.0
U12=$L/libunity-gtk4-menu.so.0; U11=/tmp/u11/x/usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0
echo "== $(date -u +%FT%TZ); 0.12 $(file $U12 | grep -o 'BuildID\[sha1\]=[0-9a-f]*' | cut -c15-30)"
run() { timeout 120 dbus-run-session -- xvfb-run -a env UNITY_GTK4_MENU_FORCE=1 ${UNITY_GTK4_MENU_DEBUG:+UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=$UNITY_GTK4_MENU_LOG} LD_PRELOAD="$1" $B/maptest 10000 2>/dev/null | grep -oE '[0-9.,]+ us per cycle' | cut -d' ' -f1; }
for form in ${FORMS:-none 0.11 0.12}; do
  case $form in none) pre= ;; 0.11) pre=$U11:$N ;; 0.12) pre=$U12:$N ;; esac
  echo "  $form: $(for i in 1 2 3 4 5; do run "$pre"; done | xargs) us per cycle"
done
echo "-- 0.12 under bpftrace (uprobes on $U12)"
sudo bpftrace -e "
uprobe:$U12:0x1aa0 { @button_map = count(); @t[tid] = nsecs; }
uretprobe:$U12:0x1aa0 /@t[tid]/ { @button_map_ns = sum(nsecs - @t[tid]); @t[tid] = 0; }
uprobe:$U12:0x1b00 { @bar_map = count(); }
" > /tmp/cost-bt.txt 2>&1 &
bt=$!; sleep 6
rm -f /tmp/cost-ugm.log
echo "  run under bpftrace: $(UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=/tmp/cost-ugm.log run "$U12:$N") us per cycle"
echo "  library log: $(grep -c 'late look' /tmp/cost-ugm.log) late looks, $(grep -c 'waits for a menu' /tmp/cost-ugm.log) waits, $(grep -c 'filled' /tmp/cost-ugm.log) fills"
sudo kill -INT $bt; wait $bt 2>/dev/null
grep -vE '^Attaching|^$' /tmp/cost-bt.txt | sed 's/^/  /'
