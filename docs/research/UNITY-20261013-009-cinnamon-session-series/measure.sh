#!/bin/bash
# measure.sh STEP [TAG] - the cinnamon-session +unity7 series on target2 (as mike over ssh). Ordinary use and passive
# observation only. Files in ~/b-cs8, copied beforehand: unity-distro.asc, unity-distro.sources, and
# cinnamon-session-binary.unstripped (eu-unstrip of the +unity7 binary and its dbgsym: the same .text, with symbols,
# so bpftrace can probe static functions by name).
#   setup:   confirm the Clean-2 restore inside; the live archive and apt full-upgrade (cinnamon-session +unity7);
#            bpftrace and xterm; the unstripped binary put in place of the installed one (the original kept)
#   clients: in the running session: bpftrace on on_client_disconnected, _disconnect_client and end_phase (with the
#            client pointer) and on client_iochannel_watch's return value; an xterm that exits normally and one killed
#            with SIGKILL; the journal's GLib criticals of cinnamon-session (UNITY-20261013-009, -010)
#   helper:  SIGKILL of unity-fallback-mount-helper, an autostart app with X-GNOME-AutoRestart: is it started again
#            within 30 s? (UNITY-20261002-010)
#   switch:  the session switched away (dm-tool switch-to-greeter), then org.gnome.SessionManager.Logout(1) on the
#            user's bus: does the session end within 60 s? end_phase calls during it (UNITY-20260927-014)
#   logout:  a foreground logout (cinnamon-session-quit --logout --no-prompt) with the same probes, for comparison
set -u
B=~/b-cs8
BIN=/usr/lib/x86_64-linux-gnu/cinnamon-session/cinnamon-session-binary
tag=${2:-x}
uu_running() {
  for p in $(pgrep -x unattended-upgr); do
    tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q -e '/unattended-upgrade ' -e '/unattended-upgrade$' && return 0
  done
  return 1
}
wait_apt() {
  for i in $(seq 120); do
    uu_running || sudo fuser /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock > /dev/null 2>&1 || return 0
    sleep 5
  done
}
cs_pid() {   # the session manager of mike's Unity session
  for p in $(pgrep -x -u "$(id -u)" cinnamon-sessio); do
    tr '\0' ' ' < /proc/$p/cmdline | grep -q -- '--session=unity' && { echo $p; return; }
  done
}
session_env() {
  local cp; cp=$(pgrep -x compiz | head -1)
  export $(tr '\0' '\n' < /proc/$cp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR|SESSION_MANAGER|XDG_SEAT_PATH|XDG_SESSION_PATH)=')
  # dm-tool needs lightdm's seat object; the session's environment does not carry it here
  [ -n "${XDG_SEAT_PATH:-}" ] || export XDG_SEAT_PATH=/org/freedesktop/DisplayManager/Seat0
}
trace_start() {   # $1 tag; probes filtered to the session manager's pid
  local cs=$1 t=$2
  sudo nohup bpftrace -B line -e "
uprobe:$BIN:on_client_disconnected /pid == $cs/ { printf(\"%llu on_client_disconnected client=%p\n\", nsecs, arg0); }
uprobe:$BIN:_disconnect_client /pid == $cs/ { printf(\"%llu _disconnect_client client=%p\n\", nsecs, arg1); }
uprobe:$BIN:end_phase /pid == $cs/ { printf(\"%llu end_phase\n\", nsecs); }
uretprobe:$BIN:client_iochannel_watch /pid == $cs/ { printf(\"%llu client_iochannel_watch returned %d\n\", nsecs, retval); }
" > /tmp/cs8-$t.trace 2>&1 < /dev/null &
  for i in $(seq 60); do grep -q Attached /tmp/cs8-$t.trace 2>/dev/null && break; sleep 0.5; done
  echo "  bpftrace: $(head -1 /tmp/cs8-$t.trace)"
}
trace_stop() {
  for p in $(pgrep -x bpftrace); do sudo kill -INT $p; done; sleep 2
  echo "-- trace ($1)"; grep -v Attached /tmp/cs8-$1.trace | sed 's/^/  /'
}
mark() { echo "  [$(cut -d' ' -f1 /proc/uptime) s since boot] $1"; }
clients() {   # the session manager's clients, with their process (numbering differs per boot)
  local c o a p
  for c in $(seq 1 16); do
    o=/org/gnome/SessionManager/Client$c
    a=$(gdbus call --session -d org.gnome.SessionManager -o $o -m org.gnome.SessionManager.Client.GetAppId 2>/dev/null) || continue
    p=$(gdbus call --session -d org.gnome.SessionManager -o $o -m org.gnome.SessionManager.Client.GetUnixProcessId 2>/dev/null | sed -n 's/.*uint32 \([0-9]*\).*/\1/p')
    echo "  Client$c: app $a, pid ${p:-?}: $([ -n "$p" ] && [ "$p" != 0 ] && tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | cut -c1-80)"
  done
}

case $1 in
setup)
  echo "== restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
  ls -d ~/.dirty 2>&1 | sed 's/^/  /'; echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
  touch ~/.dirty
  sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
  sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
  wait_apt; sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
  grep -hE "^Date" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
  wait_apt; sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
  wait_apt; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q bpftrace xterm > /tmp/inst.log 2>&1; echo "  install rc=$?"
  dpkg-query -W cinnamon-session cinnamon-session-common libsm6 libice6 libglib2.0-0t64 unity-session | sed 's/^/  /'
  echo "  installed binary build-id $(readelf -n $BIN | awk '/Build ID/{print $3}')"
  sudo cp -p $BIN $BIN.orig && sudo install -m755 $B/cinnamon-session-binary.unstripped $BIN
  echo "  unstripped in place: build-id $(readelf -n $BIN | awk '/Build ID/{print $3}'), symbols $(nm $BIN 2>/dev/null | grep -c -E ' t (on_client_disconnected|_disconnect_client|end_phase|client_iochannel_watch)$')"
  ;;
base)
  # for a test build: Clean-2 -> live, full-upgrade, bpftrace and xterm; no binary replaced
  echo "== restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
  ls -d ~/.dirty 2>&1 | sed 's/^/  /'; echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
  touch ~/.dirty
  sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
  sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
  wait_apt; sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
  grep -hE "^Date" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
  wait_apt; sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
  wait_apt; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q bpftrace xterm > /tmp/inst.log 2>&1; echo "  install rc=$?"
  dpkg-query -W cinnamon-session cinnamon-session-common | sed 's/^/  /'
  ;;
install)
  # the test build's debs (in $B), then its unstripped binary (same .text, with symbols) in place of the installed one
  sha256sum $B/*.deb | cut -c1-16,65- | sed 's/^/  /'
  wait_apt; sudo dpkg -i $B/cinnamon-session_*.deb $B/cinnamon-session-common_*.deb > /tmp/dpkg.log 2>&1; echo "  dpkg -i rc=$?"
  dpkg-query -W cinnamon-session cinnamon-session-common | sed 's/^/  /'
  dpkg -V cinnamon-session cinnamon-session-common; echo "  dpkg -V rc=$?"
  echo "  installed binary sha256 $(sha256sum < $BIN | cut -c1-16)"
  sudo cp -p $BIN $BIN.orig && sudo install -m755 $B/cinnamon-session-binary.unstripped $BIN
  echo "  unstripped in place: sha256 $(sha256sum < $BIN | cut -c1-16), symbols $(nm $BIN 2>/dev/null | grep -c -E ' t (on_client_disconnected|_disconnect_client|end_phase|client_iochannel_watch)$')"
  ;;
clients)
  session_env; cs=$(cs_pid)
  echo "== clients at $(date -u +%FT%TZ), boot $(uptime -s); $(dpkg-query -W -f='cinnamon-session ${Version}' cinnamon-session); pid $cs"
  trace_start $cs $tag
  echo "-- xterm, normal exit"
  xterm -e sh -c 'sleep 4' & x1=$!; sleep 2; mark "xterm 1 running"; sleep 5; wait $x1; echo "  xterm 1 exited: $?"
  sleep 2; mark "after xterm 1"
  echo "-- xterm, SIGKILL"
  xterm -e sh -c 'sleep 60' & x2=$!; sleep 5; mark "xterm 2 running"; kill -9 $x2; wait $x2 2>/dev/null; echo "  xterm 2 killed: status $?"
  sleep 3; mark "after the kill"
  trace_stop $tag
  echo "-- GLib criticals and warnings of cinnamon-session in this boot's journal"
  journalctl -b --no-pager -q -o short-monotonic | grep -E "cinnamon-session.*(CRITICAL|WARNING)|Source ID" | sed 's/^/  /' | tail -20
  ;;
helper)
  session_env; cs=$(cs_pid)
  echo "== helper at $(date -u +%FT%TZ); pid $cs"
  grep -h -E "^(Exec|X-GNOME-AutoRestart|OnlyShowIn|X-GNOME-Autostart-Phase)=" /etc/xdg/autostart/unity-fallback-mount-helper.desktop | sed 's/^/  /'
  h=$(pgrep -x -u "$(id -u)" unity-fallback- | head -1); echo "  before: unity-fallback-mount-helper pid ${h:-none}"
  [ -n "$h" ] && { kill -9 $h; mark "SIGKILL sent to $h"; }
  for i in $(seq 30); do n=$(pgrep -x -u "$(id -u)" unity-fallback- | head -1); [ -n "$n" ] && [ "$n" != "$h" ] && break; sleep 1; done
  echo "  after 30 s: unity-fallback-mount-helper pid ${n:-none}$([ -n "$n" ] && [ "$n" != "$h" ] && echo ' (restarted)' || echo ' (not restarted)')"
  journalctl -b --no-pager -q -o short-monotonic --since "-1min" | grep -i -E "fallback-mount|restart" | sed 's/^/  /' | tail -8
  ;;
switch)
  session_env; cs=$(cs_pid)
  echo "== switch at $(date -u +%FT%TZ); pid $cs"
  echo "-- clients"; clients
  trace_start $cs $tag
  dm-tool switch-to-greeter; sleep 5
  echo "  loginctl: $(loginctl list-sessions --no-legend | xargs)"
  echo "  mike's session active: $(loginctl show-session $(loginctl list-sessions --no-legend | awk '$3=="mike" && $4=="seat0" {print $1}' | head -1) -p Active --value 2>&1)"
  mark "Logout(1)"
  gdbus call --session -d org.gnome.SessionManager -o /org/gnome/SessionManager -m org.gnome.SessionManager.Logout 1 2>&1 | sed 's/^/  gdbus: /'
  for i in $(seq 150); do kill -0 $cs 2>/dev/null || break; sleep 1; done
  mark "after up to 150 s: cinnamon-session pid $cs $(kill -0 $cs 2>/dev/null && echo 'STILL RUNNING' || echo gone)"
  trace_stop $tag
  journalctl -b --no-pager -q -o short-monotonic --since "-4min" | grep -E "cinnamon-session|csm" | sed 's/^/  /' | tail -15
  ;;
stopped)
  # UNITY-20260929-007, allowed by C (2026-10-13): at-spi-registryd stopped with SIGSTOP during a logout (an
  # unresponsive client, no crafted input), a second logout request while the first waits, then SIGCONT
  session_env; cs=$(cs_pid)
  echo "== stopped at $(date -u +%FT%TZ); pid $cs"
  echo "-- inhibitors before"
  gdbus call --session -d org.gnome.SessionManager -o /org/gnome/SessionManager -m org.gnome.SessionManager.GetInhibitors 2>&1 | sed 's/^/  /'
  a=$(pgrep -x -u "$(id -u)" at-spi2-registr | head -1); echo "  at-spi2-registryd pid ${a:-none}"
  echo "-- clients"; clients
  trace_start $cs $tag
  [ -n "$a" ] && { kill -STOP $a; mark "SIGSTOP $a"; }
  mark "cinnamon-session-quit --logout --no-prompt"
  ( cinnamon-session-quit --logout --no-prompt 2>&1 | grep -v Deprecat | sed 's/^/  quit 1: /' ) &
  sleep 10
  mark "second request: Logout(1)"
  gdbus call --session -d org.gnome.SessionManager -o /org/gnome/SessionManager -m org.gnome.SessionManager.Logout 1 2>&1 | sed 's/^/  gdbus: /'
  for i in $(seq 50); do kill -0 $cs 2>/dev/null || break; sleep 1; done
  mark "60 s after the first request: cinnamon-session pid $cs $(kill -0 $cs 2>/dev/null && echo 'STILL RUNNING' || echo gone)"
  [ -n "$a" ] && { kill -CONT $a 2>/dev/null; mark "SIGCONT $a"; }
  for i in $(seq 60); do kill -0 $cs 2>/dev/null || break; sleep 1; done
  mark "after SIGCONT (up to 60 s): cinnamon-session pid $cs $(kill -0 $cs 2>/dev/null && echo 'STILL RUNNING' || echo gone)"
  trace_stop $tag
  journalctl -b --no-pager -q -o short-monotonic --since "-3min" | grep -E "cinnamon-session|csm|NotInRunning|at-spi" | sed 's/^/  /' | tail -20
  ;;
slow)
  # UNITY-20260927-014 round 2 (allowed by C, 2026-10-17): the slow XSMP client (xsmp-slow DELAY HOLD) answers the
  # end-session query with an InteractRequest DELAY s late, closes HOLD s after that; the session is switched away
  # and Logout(1) is requested. Expected: the logout is held while the client holds, then goes on.
  session_env; cs=$(cs_pid)
  echo "== slow at $(date -u +%FT%TZ); pid $cs; $(dpkg-query -W -f='cinnamon-session ${Version}' cinnamon-session)"
  nohup $B/xsmp-slow ${3:-3} ${4:-45} > /tmp/cs8-slow-$tag.txt 2>&1 < /dev/null &
  sleep 3; echo "  xsmp-slow: $(head -1 /tmp/cs8-slow-$tag.txt)"
  echo "-- clients"; clients
  dm-tool switch-to-greeter; sleep 5
  echo "  mike's session active: $(loginctl show-session $(loginctl list-sessions --no-legend | awk '$3=="mike" && $4=="seat0" {print $1}' | head -1) -p Active --value 2>&1)"
  mark "Logout(1)"
  gdbus call --session -d org.gnome.SessionManager -o /org/gnome/SessionManager -m org.gnome.SessionManager.Logout 1 2>&1 | sed 's/^/  gdbus: /'
  for i in $(seq 150); do kill -0 $cs 2>/dev/null || break; sleep 1; done
  mark "after up to 150 s: cinnamon-session pid $cs $(kill -0 $cs 2>/dev/null && echo 'STILL RUNNING' || echo gone)"
  echo "-- xsmp-slow"; sed 's/^/  /' /tmp/cs8-slow-$tag.txt
  journalctl -b --no-pager -q -o short-monotonic --since "-4min" | grep -E "cinnamon-session-binary\[" | grep -E "WARNING|CRITICAL|dialog|reply" | sed 's/^/  /' | tail -12
  ;;
logout)
  session_env; cs=$(cs_pid)
  echo "== logout at $(date -u +%FT%TZ); pid $cs"
  trace_start $cs $tag
  mark "cinnamon-session-quit --logout --no-prompt"
  cinnamon-session-quit --logout --no-prompt 2>&1 | grep -v Deprecat | sed 's/^/  /'
  for i in $(seq 60); do kill -0 $cs 2>/dev/null || break; sleep 1; done
  mark "after up to 60 s: cinnamon-session pid $cs $(kill -0 $cs 2>/dev/null && echo 'STILL RUNNING' || echo gone)"
  trace_stop $tag
  ;;
esac
