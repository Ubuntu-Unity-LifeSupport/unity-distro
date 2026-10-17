#!/bin/bash
# probe.sh STEP - UNITY-20261017-002 on target2 (as mike over ssh): what compiz's threads are doing while the session
# is switched away, and whether its XSMP (ICE) socket holds unread data. Passive only: /proc and ss, no ptrace, no
# debugger, nothing written to compiz.
#   snap:   one snapshot now (a dry run)
#   idle:   snapshots while the session is active, then dm-tool switch-to-greeter and snapshots for 60 s (no logout)
#   logout: switched away (as left by idle), org.gnome.SessionManager.Logout(1), snapshots until compiz is gone
# A snapshot: per thread of compiz, its state, wchan and current syscall (/proc/PID/task/TID/{stat,wchan,syscall}),
# compiz's CPU time, its unix sockets' receive queues with their peers, and the session manager's ICE sockets, so
# that compiz's ICE connection is found by matching inodes.
set -u
session_env() {
  local cp; cp=$(pgrep -x compiz | head -1)
  export $(tr '\0' '\n' < /proc/$cp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR|SESSION_MANAGER)=')
  # dm-tool needs lightdm's seat object; the session's environment does not carry it here
  export XDG_SEAT_PATH=/org/freedesktop/DisplayManager/Seat0
}
syscall_name() { # x86_64 numbers seen in an event loop or a GL wait
  case $1 in
    7) echo poll ;; 271) echo ppoll ;; 232) echo epoll_wait ;; 281) echo epoll_pwait ;; 202) echo futex ;;
    16) echo ioctl ;; 0) echo read ;; 1) echo write ;; 23) echo select ;; 270) echo pselect6 ;; 35) echo nanosleep ;;
    230) echo clock_nanosleep ;; 47) echo recvmsg ;; 46) echo sendmsg ;; running) echo running ;; *) echo "nr $1" ;;
  esac
}
socks() { # $1 pid, $2 1 = only ICE sockets: Recv-Q, local path, local inode, peer inode
  ss -xpn 2>/dev/null | awk -v p="pid=$1," -v ice="$2" \
    'index($0, p) && (ice == 0 || index($0, ".ICE-unix")) { print "    recvq " $3 "  local " $5 " " $6 "  peer " $8 }'
}
snap() {
  local cp=$1 tag=$2
  echo "-- $tag at $(date -u +%T.%3NZ), session active: $(loginctl show-session "$SID" -p Active --value)"
  sed 's/.*) //' /proc/$cp/stat | awk '{ print "  cpu utime+stime ticks: " $12 + $13 }'
  for t in /proc/$cp/task/*; do
    local tid=${t##*/} st wc sc
    st=$(sed 's/.*) //' $t/stat 2>/dev/null | cut -d' ' -f1)
    wc=$(cat $t/wchan 2>/dev/null)
    # reading syscall needs ptrace read access (Yama); it is still only a read of /proc
    sc=$(sudo cat $t/syscall 2>/dev/null | cut -d' ' -f1)
    printf '  tid %-6s %-16s state %s  wchan %-24s syscall %s\n' "$tid" "$(cat $t/comm)" "$st" "${wc:-0}" "$(syscall_name "${sc:-?}")"
  done
  echo "  compiz's unix sockets:"; socks $cp 0
  echo "  the session manager's ICE sockets:"; socks $CS 1
}
session_env
CP=$(pgrep -x compiz | head -1)
CS=$(pgrep -x cinnamon-sessio | head -1)
SID=$(loginctl show-user "$USER" -p Display --value)
case $1 in
snap)
  snap $CP "dry run"
  ;;
idle)
  echo "== idle at $(date -u +%FT%TZ), boot $(uptime -s); compiz $CP, cinnamon-session $CS"
  dpkg-query -W compiz-core cinnamon-session 2>&1 | sed 's/^/  /'
  echo "  SESSION_MANAGER=$SESSION_MANAGER"
  echo "  GL: $(glxinfo -B 2>/dev/null | grep -E 'OpenGL renderer|direct rendering' | xargs)"
  snap $CP "active 1"; sleep 5; snap $CP "active 2"
  dm-tool switch-to-greeter; echo "  dm-tool switch-to-greeter rc=$?"
  for i in 1 2 3 4 5 6; do sleep 10; snap $CP "switched away, +$((i * 10)) s"; done
  ;;
logout)
  echo "== logout at $(date -u +%FT%TZ); compiz $CP"
  snap $CP "before Logout(1)"
  gdbus call --session -d org.gnome.SessionManager -o /org/gnome/SessionManager -m org.gnome.SessionManager.Logout 1 > /dev/null 2>&1 &
  echo "  Logout(1) sent at $(date -u +%T.%3NZ)"
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14; do
    sleep 5
    kill -0 $CP 2>/dev/null || { echo "  compiz $CP gone at $(date -u +%T.%3NZ)"; break; }
    snap $CP "after Logout(1), +$((i * 5)) s"
  done
  ;;
esac
