#!/bin/sh
# UNITY-20260927-040: the release build's check on target - the regression
# test and a sample of the test plan (section 7) on one boot. Run as mike.
# usage: release-sample.sh OUT
O=${1:?outdir}; mkdir -p "$O"
. ~/envt.sh
echo "=== boot $(uptime -s) | $(dpkg-query -W unity libunity-core-6.0-9 compiz | paste -sd' ')"
P=$(pgrep -x compiz)
echo "=== compiz $P, deleted library mappings: $(grep '(deleted)' /proc/$P/maps | grep -c '\.so'), libunityshell sha256 $(sha256sum /usr/lib/x86_64-linux-gnu/compiz/libunityshell.so | cut -c1-16)"
xdotool set_desktop_viewport 0 0
counts() { echo "  $1 edge=$(grep -c EDGE-DOWN "$2") ungrab-from-decorations=$(grep -A2 -E 'XUNGRAB(POINTER|KEYBOARD)$' "$2" | grep -c 'HandleFrameEvent\|GrabEdge') expo-removed=$(grep -c REMOVE-GRAB "$2")"; }
echo "=== (1) regression: title drag in expo x5"
SCEN=after-tests.sh sh ~/grab-series.sh expo-title 5 "$O/expo-title" | grep SUMMARY
for i in 1 2 3 4 5; do counts expo-title-$i "$O/expo-title/expo-title-$i.txt"; done
echo "=== (1b) replay orig x2, noborder x1"
for i in 1 2; do sh ~/replay-stuck1.sh "$O/replay" $i orig | grep -E 'b trace|active grabs'; done
sh ~/replay-stuck1.sh "$O/replay" 1 noborder | grep -E 'b trace|active grabs'
echo "=== (2) expo-border x2"
sh ~/grab-series.sh expo-border 2 "$O/expo" | grep SUMMARY
for i in 1 2; do counts expo-border-$i "$O/expo/expo-border-$i.txt"; done
echo "=== (3)(4) title bar, first press after expo"
for v in title-immediate title-motion after-expo; do
  SCEN=after-tests.sh sh ~/uprobetrace-040.sh $v "$O/after-$v.txt"
  echo "  $(cut -c1-180 "$O/after-$v.txt.result")"
done
echo "=== (5) keyboard resize, border reached"
sh ~/grab-series.sh kbdresize-drag 2 "$O/kbd" | grep SUMMARY
for i in 1 2; do counts kbdresize-drag-$i "$O/kbd/kbdresize-drag-$i.txt"; done
echo "=== (6) UNITY-20260927-001 #3 sample"
for v in rmbslow titlemovermb; do
  bash ~/resize-series.sh $v 3 > "$O/rg-$v.log" 2>&1
  echo "  $v stuck=$(grep -c STUCK "$O/rg-$v.log")/3 | $(head -1 "$O/rg-$v.log" | cut -c1-120)"
done
echo "=== done $(date -u +%H:%M:%SZ)"
