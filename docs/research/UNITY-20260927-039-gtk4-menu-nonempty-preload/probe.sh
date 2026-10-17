#!/bin/bash
# probe.sh STEP TAG - UNITY-20260927-039 on target2 (as mike over ssh): does libunity-gtk4-menu stay in the session's
# preload when the user's own session LD_PRELOAD is not empty? The case of UNITY-20260927-022 logs/06: ~/.xsessionrc
# exports LD_PRELOAD=libm.so.6 (a harmless library), 51gtk-nocsd adds gtk-nocsd, and 95dbus_update-activation-env
# --all imports the X session's LD_PRELOAD into the user manager over environment.d's value.
#   setup:  confirm the Clean-2 restore inside; the live archive and apt full-upgrade; gnome-calculator (a GTK4
#           application with a header-bar menu)
#   rc:     write ~/.xsessionrc with `export LD_PRELOAD=libm.so.6` (the next boot is the measured one)
#   probe:  versions, the snippets and environment.d files, LD_PRELOAD of the user manager and of the session
#           processes, and a GTK4 application started through the user manager: does it map libunity-gtk4-menu and
#           export a menubar (_GTK_MENUBAR_OBJECT_PATH)?
set -u
B=~/b039
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
env_of() { tr '\0' '\n' < /proc/$1/environ 2>/dev/null | sed -n 's/^LD_PRELOAD=//p'; }
case $1 in
setup)
  echo "== restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
  ls -d ~/.dirty ~/.xsessionrc 2>&1 | sed 's/^/  /'; echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
  touch ~/.dirty
  sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
  sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
  wait_apt; sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
  grep -hE "^Date" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
  wait_apt; sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
  wait_apt; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q gnome-calculator xdotool x11-utils > /tmp/inst.log 2>&1; echo "  install rc=$?"
  ;;
rc)
  echo 'export LD_PRELOAD=libm.so.6' > ~/.xsessionrc
  echo "  ~/.xsessionrc: $(cat ~/.xsessionrc)"
  ;;
probe)
  tag=$2
  cp=$(pgrep -x compiz | head -1)
  export $(tr '\0' '\n' < /proc/$cp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR)=')
  echo "== $tag at $(date -u +%FT%TZ), boot $(uptime -s)"
  dpkg-query -W libgtk-nocsd0 libunity-gtk4-menu0 unity-session dbus-x11 dbus-user-session 2>&1 | sed 's/^/  /'
  echo "  xsessionrc: $(cat ~/.xsessionrc 2>/dev/null || echo none)"
  echo "-- the snippets"
  ls /etc/X11/Xsession.d/ | grep -i -E "nocsd|gtk4|menu|dbus" | sed 's/^/  Xsession.d: /'
  for f in /usr/lib/environment.d/*nocsd* /usr/lib/environment.d/*gtk4* /usr/lib/environment.d/*menu*; do
    [ -f "$f" ] && echo "  $f: $(grep -v '^#' "$f" | xargs)"
  done
  echo "-- LD_PRELOAD"
  echo "  user manager: $(systemctl --user show-environment | sed -n 's/^LD_PRELOAD=//p')"
  for n in compiz unity-panel-ser hud-service; do
    p=$(pgrep -x -u "$(id -u)" $n | head -1); echo "  $n: $(env_of $p)"
  done
  echo "-- a GTK4 application started through the user manager (gnome-calculator)"
  systemd-run --user --quiet --unit=b039-$tag gnome-calculator; sleep 8
  pid=$(systemctl --user show b039-$tag -p MainPID --value)
  echo "  pid $pid LD_PRELOAD: $(env_of $pid)"
  echo "  maps: $(grep -oE 'lib(gtk-nocsd|unity-gtk4-menu)\.so\.0' /proc/$pid/maps | sort -u | xargs)"
  w=$(xdotool search --onlyvisible --pid "$pid" 2>/dev/null | head -1)
  echo "  window ${w:-none}: $([ -n "$w" ] && xprop -id "$w" _GTK_MENUBAR_OBJECT_PATH 2>&1)"
  systemctl --user stop b039-$tag 2>/dev/null
  ;;
esac
