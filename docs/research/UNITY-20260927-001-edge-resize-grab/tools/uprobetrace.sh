#!/bin/sh
# UNITY-20260927-001 (agent A): trace one resize-grab.sh VARIANT inside compiz
# with uprobes (bpftrace), which do not stop the process the way gdb
# breakpoints do and so keep the event timing of the real scenario.
# Logs Edge::ButtonDownEvent (button), resize initiate (+ its return value) and
# terminate, compiz core pointer grab push/remove, XGrabPointer/XUngrabPointer
# with the calling frames. usage: uprobetrace.sh VARIANT OUTFILE
V=$1; OUT=$2; P=$(pgrep -x compiz)
U=/usr/lib/x86_64-linux-gnu/compiz/libunityshell.so
R=/usr/lib/x86_64-linux-gnu/compiz/libresize.so
C=/usr/lib/x86_64-linux-gnu/libcompiz_core.so.0.9.14.2
X=/usr/lib/x86_64-linux-gnu/libX11.so.6
cat > /tmp/uprobetrace.bt <<B
uprobe:$U:_ZN5unity10decoration4Edge15ButtonDownEventERK9CompPointjm /pid == $P/ { printf("%d EDGE-DOWN button=%d\n", elapsed/1000000, arg2); }
uprobe:$U:_ZN5unity10decoration8GrabEdge15ButtonDownEventERK9CompPointjm /pid == $P/ { printf("%d GRABEDGE-DOWN button=%d\n", elapsed/1000000, arg2); }
uprobe:$R:_ZN11ResizeLogic14initiateResizeEP10CompActionjRSt6vectorI10CompOptionSaIS3_EEj /pid == $P/ { printf("%d RESIZE-INITIATE state=%d\n", elapsed/1000000, arg2); }
uretprobe:$R:_ZN11ResizeLogic14initiateResizeEP10CompActionjRSt6vectorI10CompOptionSaIS3_EEj /pid == $P/ { printf("%d RESIZE-INITIATE returned %d\n", elapsed/1000000, retval & 0xff); }
uprobe:$R:_ZN11ResizeLogic15terminateResizeEP10CompActionjRSt6vectorI10CompOptionSaIS3_EE /pid == $P/ { printf("%d RESIZE-TERMINATE state=%d\n", elapsed/1000000, arg2); }
uprobe:$C:_ZN14CompScreenImpl15pushPointerGrabEmPKc /pid == $P/ { printf("%d PUSH-POINTER-GRAB %s\n", elapsed/1000000, str(arg2)); }
uprobe:$C:_ZN14CompScreenImpl8pushGrabEmPKc /pid == $P/ { printf("%d PUSH-GRAB %s\n", elapsed/1000000, str(arg2)); }
uprobe:$C:_ZN14CompScreenImpl10removeGrabEPN6compiz14private_screen4GrabEP9CompPoint /pid == $P/ { printf("%d REMOVE-GRAB\n", elapsed/1000000); }
uprobe:$X:XGrabPointer /pid == $P/ { printf("%d XGRABPOINTER%s\n", elapsed/1000000, ustack(4)); }
uprobe:$X:XUngrabPointer /pid == $P/ { printf("%d XUNGRABPOINTER%s\n", elapsed/1000000, ustack(4)); }
BEGIN { printf("READY\n"); }
B
sudo -n timeout 30 bpftrace /tmp/uprobetrace.bt > "$OUT" 2>&1 &
for i in $(seq 1 30); do sleep 0.5; grep -q READY "$OUT" 2>/dev/null && break; done
DISPLAY=:0 ~/${SCEN:-resize-grab.sh} "$V" > "$OUT.result" 2>&1
wait
