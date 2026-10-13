#!/bin/bash
# cost-bt.sh - on target2 (as mike over ssh, in the Unity session): the shim's calls and the time spent in them, with
# bpftrace uprobes by name. bpftrace cannot place probes in the shipped, stripped library, so this preloads
# ~/b1204t/libunity-gtk4-menu.so.0.unstripped instead: the shipped 0.12 file joined with its dbgsym by eu-unstrip
# (same .text, checked on the builder), for this measurement only.
#   maptest: an application window without a menu, one GtkMenuButton hidden and shown 10 000 times (Xvfb).
#   pinta:   Pinta 3.1.2 in the session (environment from compiz, LD_PRELOAD pointing at the copy), 20 s from start.
# Counts: shim_menu_button_map, shim_menu_bar_map, look_idle, look; total ns in the two shims and in look.
set -u
B=~/b1204t; L=/usr/lib/x86_64-linux-gnu; N=$L/libgtk-nocsd.so.0; U=$B/libunity-gtk4-menu.so.0.unstripped
probe() {  # probe OUT: bpftrace on $U for any process, to OUT
  sudo bpftrace -e "
uprobe:$U:shim_menu_button_map { @calls[\"shim_menu_button_map\"] = count(); @t1[tid] = nsecs; }
uretprobe:$U:shim_menu_button_map /@t1[tid]/ { @ns[\"shims\"] = sum(nsecs - @t1[tid]); @t1[tid] = 0; }
uprobe:$U:shim_menu_bar_map { @calls[\"shim_menu_bar_map\"] = count(); @t2[tid] = nsecs; }
uretprobe:$U:shim_menu_bar_map /@t2[tid]/ { @ns[\"shims\"] = sum(nsecs - @t2[tid]); @t2[tid] = 0; }
uprobe:$U:look_idle { @calls[\"look_idle\"] = count(); }
uprobe:$U:look { @calls[\"look\"] = count(); @t3[tid] = nsecs; }
uretprobe:$U:look /@t3[tid]/ { @ns[\"look\"] = sum(nsecs - @t3[tid]); @t3[tid] = 0; }
" > "$1" 2>&1 &
  echo $!
}
echo "== $(date -u +%FT%TZ); copy $(file $U | grep -o 'BuildID\[sha1\]=[0-9a-f]*' | cut -c15-30)"
echo "-- maptest, 10 000 cycles"
bt=$(probe /tmp/bt-map.txt); sleep 6
timeout 120 dbus-run-session -- xvfb-run -a env UNITY_GTK4_MENU_FORCE=1 LD_PRELOAD=$U:$N $B/maptest 10000 2>/dev/null | grep cycles | sed 's/^/  /'
sleep 3; sudo kill -INT $(pgrep -x bpftrace) 2>/dev/null; sleep 5; grep -vE '^Attaching|^$' /tmp/bt-map.txt | sed 's/^/  /'
echo "-- Pinta, 20 s from start"
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
pkill -x Pinta; sleep 1; rm -f /tmp/ugm-cost-pinta.log
bt=$(probe /tmp/bt-pinta.txt); sleep 6
env -i "${envs[@]}" LD_PRELOAD=$U:$N UNITY_GTK4_MENU_DEBUG=1 UNITY_GTK4_MENU_LOG=/tmp/ugm-cost-pinta.log DOTNET_ROLL_FORWARD=Major \
  ~/b1204/Pinta-3.1.2/build/bin/Pinta > /dev/null 2>&1 & p=$!
sleep 20
echo "  Pinta pid $p, maps: $(grep -oE 'libunity-gtk4-menu[^ ]*' /proc/$p/maps | sort -u | xargs); log: $(grep -c 'late look' /tmp/ugm-cost-pinta.log) late looks, $(grep -c 'filled late' /tmp/ugm-cost-pinta.log) late fills"
sleep 3; sudo kill -INT $(pgrep -x bpftrace) 2>/dev/null; sleep 5; grep -vE '^Attaching|^$' /tmp/bt-pinta.txt | sed 's/^/  /'
kill $p 2>/dev/null
