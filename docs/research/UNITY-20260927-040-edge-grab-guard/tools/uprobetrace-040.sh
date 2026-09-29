#!/bin/sh
# UNITY-20260927-040 (agent A): run one tools/grab-edge.sh VARIANT under
# bpftrace uprobes in compiz (no process stop; UNITY-20260927-001's
# uprobetrace.sh extended with keyboard grabs, move and expo). Logs
# Edge::ButtonDownEvent (button) and whether Edge then ungrabs, compiz grab
# push/remove with names, move/resize initiate/terminate, X pointer and
# keyboard grab/ungrab calls with the calling frames, and the button events
# UnityScreen::handleEvent and ExpoScreen::handleEvent receive (XEvent type at
# offset 0, xbutton.window at 32, xbutton.button at 84 on x86_64).
# usage: uprobetrace-040.sh VARIANT OUTFILE
V=$1; OUT=$2; P=$(pgrep -x compiz)
U=/usr/lib/x86_64-linux-gnu/compiz/libunityshell.so
R=/usr/lib/x86_64-linux-gnu/compiz/libresize.so
MV=/usr/lib/x86_64-linux-gnu/compiz/libmove.so
E=/usr/lib/x86_64-linux-gnu/compiz/libexpo.so
C=/usr/lib/x86_64-linux-gnu/libcompiz_core.so.0.9.14.2
X=/usr/lib/x86_64-linux-gnu/libX11.so.6
cat > /tmp/uprobetrace-040.bt <<B
uprobe:$U:_ZN5unity10decoration4Edge15ButtonDownEventERK9CompPointjm /pid == $P/ { printf("%d EDGE-DOWN button=%d\n", elapsed/1000000, arg2); }
uprobe:$U:_ZN5unity10decoration8GrabEdge15ButtonDownEventERK9CompPointjm /pid == $P/ { printf("%d GRABEDGE-DOWN button=%d\n", elapsed/1000000, arg2); }
uprobe:$R:_ZN11ResizeLogic14initiateResizeEP10CompActionjRSt6vectorI10CompOptionSaIS3_EEj /pid == $P/ { printf("%d RESIZE-INITIATE state=%d\n", elapsed/1000000, arg2); }
uprobe:$R:_ZN11ResizeLogic15terminateResizeEP10CompActionjRSt6vectorI10CompOptionSaIS3_EE /pid == $P/ { printf("%d RESIZE-TERMINATE state=%d\n", elapsed/1000000, arg2); }
uprobe:$C:_ZN14CompScreenImpl15pushPointerGrabEmPKc /pid == $P/ { printf("%d PUSH-POINTER-GRAB %s\n", elapsed/1000000, str(arg2)); }
uprobe:$C:_ZN14CompScreenImpl8pushGrabEmPKc /pid == $P/ { printf("%d PUSH-GRAB %s\n", elapsed/1000000, str(arg2)); }
uprobe:$C:_ZN14CompScreenImpl10removeGrabEPN6compiz14private_screen4GrabEP9CompPoint /pid == $P/ { printf("%d REMOVE-GRAB\n", elapsed/1000000); }
uprobe:$X:XGrabPointer /pid == $P/ { printf("%d XGRABPOINTER%s\n", elapsed/1000000, ustack(4)); }
uprobe:$X:XUngrabPointer /pid == $P/ { printf("%d XUNGRABPOINTER%s\n", elapsed/1000000, ustack(4)); }
uprobe:$X:XGrabKeyboard /pid == $P/ { printf("%d XGRABKEYBOARD%s\n", elapsed/1000000, ustack(4)); }
uprobe:$X:XUngrabKeyboard /pid == $P/ { printf("%d XUNGRABKEYBOARD%s\n", elapsed/1000000, ustack(4)); }
uprobe:$E:_ZN10ExpoScreen11handleEventEP7_XEvent /pid == $P && (*(int32*)arg1 == 4 || *(int32*)arg1 == 5)/ { printf("%d EXPO-SEES %s window=0x%x button=%d\n", elapsed/1000000, *(int32*)arg1 == 4 ? "ButtonPress" : "ButtonRelease", *(uint64*)(arg1 + 32), *(uint32*)(arg1 + 84)); }
uprobe:$U:_ZN5unity11UnityScreen11handleEventEP7_XEvent /pid == $P && (*(int32*)arg1 == 4 || *(int32*)arg1 == 5)/ { printf("%d UNITY-SEES %s window=0x%x button=%d\n", elapsed/1000000, *(int32*)arg1 == 4 ? "ButtonPress" : "ButtonRelease", *(uint64*)(arg1 + 32), *(uint32*)(arg1 + 84)); }
BEGIN { printf("READY\n"); }
B
# move plugin symbols differ between builds; probe them only if present
for s in $(nm -D --defined-only $MV 2>/dev/null | awk '/moveInitiate|moveTerminate/ {print $3}'); do
  echo "uprobe:$MV:$s /pid == $P/ { printf(\"%d MOVE $s\\n\", elapsed/1000000); }" >> /tmp/uprobetrace-040.bt
done
sudo -n timeout 40 bpftrace /tmp/uprobetrace-040.bt > "$OUT" 2>&1 &
for i in $(seq 1 40); do sleep 0.5; grep -q READY "$OUT" 2>/dev/null && break; done
DISPLAY=:0 ~/${SCEN:-grab-edge.sh} "$V" > "$OUT.result" 2>&1   # SCEN=after-tests.sh for those variants
wait
