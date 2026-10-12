#!/bin/bash
# target-setup.sh STEP - UNITY-20261009-003/-004/-005 target check on target2 (as mike over ssh):
#   live    after a restore of Clean-2: confirm it from inside; the live archive the usual way (key + sources copied
#           to ~/b0309 beforehand); apt full-upgrade; the test helpers xdotool, x11-utils, gnome-calculator and
#           libunity-gtk4-menu0 (installed explicitly: nothing depends on it, UNITY-20260927-037)
#   unity7  hud +unity7 from a file repository of this task's build (~/b0309/repo with a Packages index made on the
#           builder: apt-utils is not on target2); every hud binary that is installed is upgraded
set -u
B=~/b0309
case $1 in
live)
  echo "== restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
  ls -d ~/.dirty ~/b0309/dev ~/b0309/repo 2>&1 | sed 's/^/  /'
  echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
  dpkg-query -W hud libunity-gtk4-menu0 2>&1 | sed 's/^/  /'
  touch ~/.dirty
  sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
  sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
  sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
  grep -hE "^Date" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
  sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
  echo "  left to upgrade: $(sudo apt-get -s full-upgrade | grep -c '^Inst')"
  P="xdotool x11-utils gnome-calculator libunity-gtk4-menu0"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst.log 2>&1; echo "  helpers rc=$?"
  dpkg-query -W hud unity gnome-terminal $P 2>&1 | sed 's/^/  /' ;;
unity7)
  echo "deb [trusted=yes] file:$B/repo ./" | sudo tee /etc/apt/sources.list.d/b0309-local.list > /dev/null
  sudo apt-get update -q > /tmp/upd2.log 2>&1; echo "  update rc=$?"
  P=""
  for d in $B/repo/*.deb; do n=$(dpkg-deb -f "$d" Package)
    dpkg-query -W -f='${Status}' "$n" 2>/dev/null | grep -q "ok installed" && P="$P $n=14.10+17.10.20170619-0ubuntu6+unity7"; done
  echo "  installing:$P"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst2.log 2>&1; echo "  install rc=$?"
  grep -E "^E:" /tmp/inst2.log | sed 's/^/  /'
  dpkg-query -W hud 2>&1 | sed 's/^/  /'; dpkg -V hud; echo "  dpkg -V rc=$?"
  for d in $B/repo/hud_*.deb; do echo "  $(basename $d) sha256 $(sha256sum < $d | cut -c1-64)"; done ;;
esac
