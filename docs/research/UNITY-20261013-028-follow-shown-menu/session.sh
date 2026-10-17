#!/bin/bash
# session.sh STEP [ARG] - T6/T7 on target2 (as mike over ssh), unity-gtk4-menu 0.14 installed, each measured boot cold
# (powered off and started from the host between steps). Based on UNITY-20260927-039's probe.sh.
#   rc CASE:    prepare the next boot - B: ~/.xsessionrc exports LD_PRELOAD=libm.so.6; C: the same, and gtk-nocsd
#               turned off for this user (~/.config/environment.d/50-gtk-nocsd.conf); F: ~/.xsessionrc exports
#               LD_PRELOAD=libunity-gtk4-menu.so.0:libm.so.6 (an old file naming ours bare); A: neither
#   probe TAG:  versions, the Xsession snippets, LD_PRELOAD of the user manager and of compiz, the panel service and
#               the HUD service, and two applications started through the user manager - gnome-calculator (C) and
#               gnome-characters (gjs): the libraries each maps and whether it exports a menubar; the session
#               journal's "cannot be preloaded" lines
#   remove:     T7 - remove libunity-gtk4-menu0 (dpkg -r --force-depends: unity-session depends on it; test machine
#               only), the conffile left in place
#   reinstall:  T7 - the package back from ~/b028t
set -u
env_of() { tr '\0' '\n' < /proc/$1/environ 2>/dev/null | sed -n 's/^LD_PRELOAD=//p'; }
case $1 in
rc)
  rm -f ~/.xsessionrc ~/.config/environment.d/50-gtk-nocsd.conf
  case $2 in
    B) echo 'export LD_PRELOAD=libm.so.6' > ~/.xsessionrc ;;
    C) echo 'export LD_PRELOAD=libm.so.6' > ~/.xsessionrc
       mkdir -p ~/.config/environment.d; : > ~/.config/environment.d/50-gtk-nocsd.conf ;;
    F) echo 'export LD_PRELOAD=libunity-gtk4-menu.so.0:libm.so.6' > ~/.xsessionrc ;;
    A) ;;
  esac
  echo "  case $2: ~/.xsessionrc: $(cat ~/.xsessionrc 2>/dev/null || echo none); nocsd opt-out: $(ls ~/.config/environment.d/50-gtk-nocsd.conf 2>/dev/null || echo none)"
  ;;
probe)
  tag=$2
  cp=$(pgrep -x compiz | head -1)
  export $(tr '\0' '\n' < /proc/$cp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR)=')
  echo "== $tag at $(date -u +%FT%TZ), boot $(uptime -s)"
  dpkg-query -W libgtk-nocsd0 libunity-gtk4-menu0 2>&1 | sed 's/^/  /'
  echo "  xsessionrc: $(cat ~/.xsessionrc 2>/dev/null || echo none); nocsd opt-out: $(ls ~/.config/environment.d/50-gtk-nocsd.conf 2>/dev/null || echo none)"
  ls /etc/X11/Xsession.d/ | grep -E "nocsd|gtk4|dbus_update" | sed 's/^/  Xsession.d: /'
  echo "  /usr/lib/environment.d/60-unity-gtk4-menu.conf: $(ls /usr/lib/environment.d/60-unity-gtk4-menu.conf 2>/dev/null || echo absent)"
  echo "-- LD_PRELOAD"
  echo "  user manager: $(systemctl --user show-environment | sed -n 's/^LD_PRELOAD=//p')"
  for n in compiz unity-panel-ser hud-service; do
    p=$(pgrep -x -u "$(id -u)" $n | head -1); echo "  $n: $(env_of $p)"
  done
  for app in gnome-calculator gnome-characters; do
    echo "-- $app, started through the user manager"
    systemd-run --user --quiet --unit=b028-$tag-$app $app; sleep 8
    pid=$(systemctl --user show b028-$tag-$app -p MainPID --value)
    echo "  pid $pid LD_PRELOAD: $(env_of $pid)"
    echo "  maps: $(grep -oE 'lib(gtk-nocsd|unity-gtk4-menu)\.so\.0' /proc/$pid/maps 2>/dev/null | sort -u | xargs)"
    w=$(xdotool search --onlyvisible --pid "$pid" 2>/dev/null | head -1)
    echo "  window ${w:-none}: $([ -n "$w" ] && xprop -id "$w" _GTK_MENUBAR_OBJECT_PATH 2>&1)"
    systemctl --user stop b028-$tag-$app 2>/dev/null
  done
  echo "-- this boot's journal: \"cannot be preloaded\" lines: $(journalctl -b --no-pager 2>/dev/null | grep -c 'cannot be preloaded')"
  journalctl -b --no-pager 2>/dev/null | grep 'cannot be preloaded' | head -3 | sed 's/^/  /'
  ;;
remove)
  echo "== remove at $(date -u +%FT%TZ)"
  sudo dpkg -r --force-depends libunity-gtk4-menu0 2>&1 | tail -2 | sed 's/^/  /'
  dpkg-query -W -f='  ${Package} ${db:Status-Abbrev} ${Version}\n' libunity-gtk4-menu0
  ls -l /etc/X11/Xsession.d/52unity-gtk4-menu /usr/lib/environment.d/60-unity-gtk4-menu.conf /usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0 2>&1 | sed 's/^/  /'
  ;;
reinstall)
  echo "== reinstall at $(date -u +%FT%TZ)"
  sudo dpkg -i ~/b028t/libunity-gtk4-menu0_0.14_amd64.deb 2>&1 | tail -1 | sed 's/^/  /'
  dpkg-query -W -f='  ${Package} ${db:Status-Abbrev} ${Version}\n' libunity-gtk4-menu0
  ;;
esac
