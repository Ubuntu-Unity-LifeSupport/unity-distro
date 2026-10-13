#!/bin/bash
# setup2.sh - UNITY-20261012-001 on target2: steps 3-5 of setup.sh again. The first run's apt-get install refused
# as a whole (rc 100) because fractal is not in resolute, so nothing of step 3 was installed and steps 4-5 failed.
# Here: one install call without fractal, plus libunity-gtk4-menu0 (our GTK4 menu component, which a full-upgrade
# does not bring in: nothing depends on it) and x11-utils (xprop, for audit.py); then the builds and Pinta.
set -u
B=~/b1012
echo "== 3 test tools and applications ($(date -u +%FT%TZ))"
P="git build-essential pkg-config libgtk-4-dev libgtk-3-dev libadwaita-1-dev gdb xdotool x11-utils python3-gi
   gir1.2-gtk-4.0 dotnet-sdk-10.0 gnome-text-editor nautilus loupe gnome-calculator baobab gnome-clocks
   libunity-gtk4-menu0"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q $P > /tmp/inst2.log 2>&1; echo "  install rc=$?"
grep -E "^E:" /tmp/inst2.log | sed 's/^/  /'
for p in $P; do dpkg-query -W -f='${Package} ${Version}\n' $p 2>/dev/null || echo "$p MISSING"; done | sed 's/^/  /'
echo "== 4 GTK-NoCSD builds"
for c in b76f3fb fd4b76a; do
  rm -rf "${B:?}/nocsd-$c"; mkdir -p $B/nocsd-$c; tar -xf $B/src/$c.tar -C $B/nocsd-$c
  (cd $B/nocsd-$c && make > $B/make-$c.log 2>&1); echo "  $c make rc=$? warnings $(grep -c 'warning:' $B/make-$c.log)"
  f=$(find $B/nocsd-$c -name '*.so*' -type f | head -1)
  echo "  $c library: ${f#$B/} sha256 $(sha256sum < "$f" | cut -c1-16)"
  cp "$f" $B/libgtk-nocsd-$c.so.0
done
echo "== 5 Pinta 3.1.2"
cd $B && git clone -q --depth 1 --branch 3.1.2 https://github.com/PintaProject/Pinta.git Pinta-3.1.2 2>&1 | tail -2
cd $B/Pinta-3.1.2 && git log --oneline -1 | sed 's/^/  /'
dotnet build -c Release Pinta/Pinta.csproj -o $B/Pinta-3.1.2/build/bin > $B/pinta-build.log 2>&1; echo "  pinta build rc=$?"
grep -E "Warn|Error|elapsed|Время" $B/pinta-build.log | tail -4 | sed 's/^/  /'
ls -la $B/Pinta-3.1.2/build/bin/Pinta 2>&1 | sed 's/^/  /'
echo "== 6 titletest"
gcc -O1 -o $B/titletest $B/titletest.c $(pkg-config --cflags --libs libadwaita-1) > $B/titletest-build.log 2>&1
echo "  titletest build rc=$? warnings $(grep -c warning: $B/titletest-build.log)"
