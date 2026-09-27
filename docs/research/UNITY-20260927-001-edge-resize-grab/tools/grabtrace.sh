#!/bin/sh
# UNITY-20260927-001 (agent A): trace one resize-grab.sh VARIANT inside compiz.
# Logs every Edge::ButtonDownEvent (button), resize initiate/terminate, compiz
# core grab push/remove (name), and each XUngrabPointer with its caller, then
# prints what grab-probe says afterwards. Needs unity-dbgsym and the compiz
# dbgsym packages matching the installed build.
# usage: grabtrace.sh VARIANT OUTFILE
V=$1; OUT=$2
P=$(pgrep -x compiz)
cat > /tmp/grabtrace.gdb <<'G'
set pagination off
set confirm off
set breakpoint pending on
handle SIGPIPE nostop noprint pass
handle SIGCHLD nostop noprint pass
handle SIGUSR1 nostop noprint pass
handle SIGUSR2 nostop noprint pass
dprintf unity::decoration::Edge::ButtonDownEvent,"EDGE-DOWN button=%u\n", button
break ResizeLogic::initiateResize
commands
silent
printf "RESIZE-INITIATE state=%u w_already=%p grabIndex=%p\n", state, this->w, this->grabIndex
continue
end
break ResizeLogic::terminateResize
commands
silent
printf "RESIZE-TERMINATE state=%u w=%p\n", state, this->w
continue
end
dprintf CompScreenImpl::pushGrab,"PUSH-GRAB all %s\n", name
dprintf CompScreenImpl::pushPointerGrab,"PUSH-GRAB pointer %s\n", name
dprintf CompScreenImpl::removeGrab,"REMOVE-GRAB %s\n", handle->name
break XUngrabPointer
commands
silent
printf "XUNGRABPOINTER from:\n"
bt 3
continue
end
continue
G
sudo -n timeout 40 gdb -q -batch -p "$P" -x /tmp/grabtrace.gdb > "$OUT" 2>&1 &
sleep 8
DISPLAY=:0 ~/resize-grab.sh "$V" >> "$OUT.result" 2>&1
sleep 30
wait
