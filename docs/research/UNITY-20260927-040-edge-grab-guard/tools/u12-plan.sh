#!/bin/sh
# UNITY-20260927-040 (agent A): the evidence card's test plan on one boot, for
# whatever unity is installed. Output: OUT/*.txt traces, results on stdout.
# usage: u12-plan.sh OUT
O=${1:?outdir}; mkdir -p "$O"
. ~/envt.sh
echo "=== boot $(uptime -s) | $(dpkg-query -W unity libunity-core-6.0-9 compiz | paste -sd' ')"
P=$(pgrep -x compiz)
echo "=== compiz $P, deleted library mappings: $(grep '(deleted)' /proc/$P/maps | grep -c '\.so')"
xdotool set_desktop_viewport 0 0
echo "=== (1) regression: title drag in expo"
SCEN=after-tests.sh sh ~/grab-series.sh expo-title 5 "$O/expo-title" | grep SUMMARY
for i in 1 2 3 4 5; do
  echo "  $i edge=$(grep -c EDGE-DOWN "$O/expo-title/expo-title-$i.txt") ungrab-from-decorations=$(grep -A2 -E 'XUNGRAB(POINTER|KEYBOARD)$' "$O/expo-title/expo-title-$i.txt" | grep -c 'HandleFrameEvent\|GrabEdge') expo-removed=$(grep -c REMOVE-GRAB "$O/expo-title/expo-title-$i.txt") release-seen=$(grep -c 'EXPO-SEES ButtonRelease' "$O/expo-title/expo-title-$i.txt")"
done
echo "=== (1b) replay of the first stuck run"
for i in 1 2 3; do sh ~/replay-stuck1.sh "$O/replay" $i orig | grep -E 'b trace|active grabs'; done
sh ~/replay-stuck1.sh "$O/replay" 1 noborder | grep -E 'b trace|active grabs'
echo "=== (2) expo series"
for v in expo-border expo-altf8-border expo-dnd-border expo-control; do
  sh ~/grab-series.sh $v 3 "$O/expo" | grep SUMMARY
  for i in 1 2 3; do
    echo "  $v-$i edge=$(grep -c EDGE-DOWN "$O/expo/$v-$i.txt") ungrab-from-decorations=$(grep -A2 -E 'XUNGRAB(POINTER|KEYBOARD)$' "$O/expo/$v-$i.txt" | grep -c 'HandleFrameEvent\|GrabEdge') expo-removed=$(grep -c REMOVE-GRAB "$O/expo/$v-$i.txt")"
  done
done
echo "=== (3)(4) title bar and first press after a grab ended"
for v in title-immediate title-hold title-motion title-dblclick after-wall after-expo; do
  for i in 1 2; do
    SCEN=after-tests.sh sh ~/uprobetrace-040.sh $v "$O/after-$v-$i.txt"
    echo "  $(cut -c1-200 "$O/after-$v-$i.txt.result") | trace: $(grep -E '^[0-9]+ (GRABEDGE-DOWN|EDGE-DOWN|PUSH-GRAB|REMOVE-GRAB)' "$O/after-$v-$i.txt" | awk '{print $2$3}' | paste -sd' ')"
  done
done
echo "=== (5) keyboard move/resize"
for v in kbdresize kbdmove kbdresize-drag kbdmove-drag; do
  sh ~/grab-series.sh $v 3 "$O/kbd" | grep SUMMARY
  for i in 1 2 3; do
    echo "  $v-$i edge=$(grep -c EDGE-DOWN "$O/kbd/$v-$i.txt") ungrab-from-decorations=$(grep -A2 -E 'XUNGRAB(POINTER|KEYBOARD)$' "$O/kbd/$v-$i.txt" | grep -c 'HandleFrameEvent\|GrabEdge') $(grep -oE 'PUSH-GRAB [a-z]+|REMOVE-GRAB' "$O/kbd/$v-$i.txt" | paste -sd' ')"
  done
done
echo "=== (6) UNITY-20260927-001 #3 regression set"
for v in rmbslow rmb rmb2 wheel mid plain titlermb titlermb2 titlewheel titlemovermb titlemovermb2 titlemovewheel titleplain; do
  bash ~/resize-series.sh $v 5 > "$O/rg-$v.log" 2>&1
  echo "  $v stuck=$(grep -c STUCK "$O/rg-$v.log")/5 | first: $(head -1 "$O/rg-$v.log" | cut -c1-150)"
done
echo "=== done $(date -u +%H:%M:%SZ)"
