#!/bin/bash
# observe.sh TAG - on target2 in the Unity session (as mike over ssh): passive observation of the session
# manager's ICE connections during ordinary use.
#   1. bpftrace on the running cinnamon-session: the return value of IceAcceptConnection (a connection is
#      accepted), and the argument of IceCloseConnection and _IceFreeConnection, with timestamps; nothing else.
#   2. ordinary use: xterm (an Xt application, an XSMP client of the session) is started in the session's
#      environment and exits normally; a second xterm is killed with SIGKILL (an application crash).
#   3. the user logs out (cinnamon-session-quit --logout --no-prompt); the trace ends with the process.
# The trace goes to /tmp/ice-TAG.txt; summary.py reads it afterwards.
set -u
tag=$1
cs=$(pgrep -f -x '/usr/lib/x86_64-linux-gnu/cinnamon-session/cinnamon-session-binary --session=unity')
cp=$(pgrep -x compiz | head -1)
export $(tr '\0' '\n' < /proc/$cp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR|SESSION_MANAGER)=')
echo "== $tag at $(date -u +%FT%TZ), boot $(uptime -s); $(dpkg-query -W -f='cinnamon-session ${Version}' cinnamon-session); cinnamon-session pid $cs"
L=/usr/lib/x86_64-linux-gnu/libICE.so.6
sudo nohup bpftrace -p "$cs" -e "
uretprobe:$L:IceAcceptConnection { printf(\"%llu accept %p\n\", nsecs, retval); }
uprobe:$L:IceCloseConnection   { printf(\"%llu close %p\n\", nsecs, arg0); }
uprobe:$L:_IceFreeConnection   { printf(\"%llu free %p\n\", nsecs, arg0); }
" > /tmp/ice-$tag.txt 2>&1 < /dev/null &
sleep 8; echo "  bpftrace: $(head -1 /tmp/ice-$tag.txt)"
# the time since boot (bpftrace's nsecs counts from boot too) and the session manager's ICE connections
mark() {
  echo "  [$(cut -d' ' -f1 /proc/uptime) s since boot] $1; connections to /tmp/.ICE-unix/$cs: $(ss -xp 2>/dev/null | grep -c "/tmp/.ICE-unix/$cs")"
}
mark "before the clients"
echo "-- xterm, normal exit"
xterm -e sh -c 'sleep 4' & x1=$!; sleep 2; mark "xterm 1 running"; sleep 5; wait $x1; echo "  xterm 1 exited: $?"
mark "after xterm 1"
echo "-- xterm, SIGKILL"
xterm -e sh -c 'sleep 60' & x2=$!; sleep 5; mark "xterm 2 running"; kill -9 $x2; wait $x2 2>/dev/null; echo "  xterm 2 killed: status $?"
sleep 3; mark "after the kill"
echo "  cinnamon-session still running: $(pgrep -f -x '/usr/lib/x86_64-linux-gnu/cinnamon-session/cinnamon-session-binary --session=unity' || echo NO)"
mark "before logout"
echo "-- logout"
cinnamon-session-quit --logout --no-prompt; echo "  cinnamon-session-quit rc=$?"
for i in $(seq 30); do kill -0 "$cs" 2>/dev/null || break; sleep 1; done
echo "  cinnamon-session pid $cs gone after logout: $(kill -0 $cs 2>/dev/null && echo NO || echo yes)"
sleep 2
echo "  crash reports newer than boot: $(find /var/crash -newermt "$(uptime -s)" -type f | wc -l)"
echo "  journal: segfault lines $(journalctl -b --no-pager -q | grep -c segfault), cinnamon-session criticals $(journalctl -b --no-pager -q | grep -c 'cinnamon-session.*CRITICAL')"
