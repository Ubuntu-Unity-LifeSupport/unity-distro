#!/bin/bash
# setup.sh - UNITY-20261012-001 on target2 (as mike over ssh), after a restore of Clean-2 and before any test:
#   1. confirm the restore from inside
#   2. the live archive the usual way (key + unity-distro.sources in ~/b1012, copied beforehand), apt full-upgrade
#   3. the test tools and applications from the archive
#   4. GTK-NoCSD b76f3fb and fd4b76a built from git archive tarballs (~/b1012/src/*.tar, copied beforehand) with the
#      project's Makefile; the packaged libgtk-nocsd.so.0 saved for restoring
#   5. Pinta 3.1.2 from its release tag, built with dotnet-sdk-10.0 (Gir.Core; runs with DOTNET_ROLL_FORWARD=Major)
set -u
B=~/b1012
echo "== 1 restore, checked inside at $(date -u +%FT%TZ), boot $(uptime -s)"
ls -d ~/.dirty ~/b1010 ~/b013 ~/b081 2>&1 | sed 's/^/  /'
echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
dpkg-query -W libgtk-nocsd0 libunity-gtk4-menu0 hud 2>&1 | sed 's/^/  /'
touch ~/.dirty
echo "== 2 live archive"
sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
sudo apt-get update -q > /tmp/upd.log 2>&1; echo "  update rc=$?"
grep -hE "^(Date)" /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  /'
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/fu.log 2>&1; echo "  full-upgrade rc=$?"
echo "  left to upgrade: $(sudo apt-get -s full-upgrade | grep -c '^Inst')"
dpkg-query -W libgtk-nocsd0 libunity-gtk4-menu0 hud unity 2>&1 | sed 's/^/  /'
echo "== 3 test tools and applications"
P="git build-essential pkg-config libgtk-4-dev libgtk-3-dev libadwaita-1-dev gdb xdotool python3-gi gir1.2-gtk-4.0
   dotnet-sdk-10.0 gnome-text-editor nautilus fractal loupe gnome-calculator baobab gnome-clocks"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst.log 2>&1; echo "  install rc=$?"
for p in $P; do dpkg-query -W -f='${Package} ${Version}\n' $p 2>/dev/null || echo "$p MISSING"; done | sed 's/^/  /'
echo "== 4 GTK-NoCSD builds"
cp /usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0 $B/libgtk-nocsd.so.0.pkg
echo "  packaged library saved: sha256 $(sha256sum < $B/libgtk-nocsd.so.0.pkg | cut -c1-16)"
for c in b76f3fb fd4b76a; do
  rm -rf "${B:?}/nocsd-$c"; mkdir -p $B/nocsd-$c; tar -xf $B/src/$c.tar -C $B/nocsd-$c
  (cd $B/nocsd-$c && make > $B/make-$c.log 2>&1); echo "  $c make rc=$? warnings $(grep -c 'warning:' $B/make-$c.log)"
  f=$(find $B/nocsd-$c -name 'libgtk-nocsd.so.0' -o -name 'GTK-NoCSD.so' | head -1); echo "  $c library: ${f#$B/} sha256 $(sha256sum < "$f" | cut -c1-16)"
  cp "$f" $B/libgtk-nocsd-$c.so.0
done
echo "== 5 Pinta 3.1.2"
cd $B && git clone -q --depth 1 --branch 3.1.2 https://github.com/PintaProject/Pinta.git Pinta-3.1.2 2>&1 | tail -2
cd $B/Pinta-3.1.2 && git log --oneline -1 | sed 's/^/  /'
dotnet build -c Release Pinta/Pinta.csproj -o $B/Pinta-3.1.2/build/bin > $B/pinta-build.log 2>&1; echo "  pinta build rc=$?"
tail -3 $B/pinta-build.log | sed 's/^/  /'
ls -la $B/Pinta-3.1.2/build/bin/Pinta 2>&1 | sed 's/^/  /'
