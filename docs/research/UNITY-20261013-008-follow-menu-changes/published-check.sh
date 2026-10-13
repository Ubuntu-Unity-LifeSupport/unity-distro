#!/bin/bash
# published-check.sh STEP - UNITY-20261013-008 on target2 (as mike over ssh): the published 0.13 from live.
# Files in ~/b008p, copied beforehand: unity-distro.asc and unity-distro.sources (the live archive).
#   prepare: confirm the Clean-2 restore inside; the live archive and apt full-upgrade; nautilus and the programs of
#            UNITY-20261013-013's session-check.sh (meld, gnome-tweaks, onboard)
#   upgrade: apt update and full-upgrade from live after the publication; the downloaded deb's sha256 against the
#            gated build's
#   optout:  the user's gtk-nocsd opt-out (an empty ~/.config/environment.d/50-gtk-nocsd.conf), for the next boot
set -u
B=~/b008p
GATED=e979cf29092d72ecdc62da988fdc943d5c51fa5ad750e58b27760597d07af99c
uu_running() {   # an unattended-upgrade run (not the always-present unattended-upgrade-shutdown daemon)
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
case $1 in
prepare)
  echo "== restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
  ls -d ~/.dirty ~/b008 ~/b008t ~/b027 2>&1 | sed 's/^/  /'
  echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
  touch ~/.dirty
  sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
  sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
  wait_apt; sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
  grep -hE "^Date" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
  wait_apt; sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
  wait_apt; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q nautilus meld gnome-tweaks onboard xdotool \
    > /tmp/inst.log 2>&1; echo "  install rc=$?"
  dpkg-query -W libunity-gtk4-menu0 libgtk-nocsd0 unity-session nautilus meld gnome-tweaks 2>&1 | sed 's/^/  /'
  ;;
upgrade)
  wait_apt; sudo apt-get update -q > /tmp/upd2.log 2>&1; echo "  update rc=$?"
  grep -hE "^Date" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
  apt-cache policy libunity-gtk4-menu0 | sed 's/^/  /'
  wait_apt; sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu2.log 2>&1; echo "  full-upgrade rc=$?"
  grep -E "libunity-gtk4-menu0" /tmp/fu2.log | sed 's/^/  apt: /'
  dpkg-query -W libunity-gtk4-menu0 | sed 's/^/  /'
  d=/var/cache/apt/archives/libunity-gtk4-menu0_0.13_amd64.deb
  s=$(sha256sum < $d | cut -d' ' -f1)
  echo "  downloaded $d sha256 $s: $([ "$s" = "$GATED" ] && echo 'equal to the gated build' || echo 'DIFFERENT from the gated build')"
  dpkg -V libunity-gtk4-menu0; echo "  dpkg -V rc=$?"
  echo "  installed library sha256 $(sha256sum < /usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0 | cut -c1-16)"
  ;;
optout)
  mkdir -p ~/.config/environment.d && : > ~/.config/environment.d/50-gtk-nocsd.conf
  ls -l ~/.config/environment.d/50-gtk-nocsd.conf | sed 's/^/  /'
  ;;
esac
