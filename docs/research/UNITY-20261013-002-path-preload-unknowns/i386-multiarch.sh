#!/bin/bash
# i386-multiarch.sh - on target2 (test target only): (a) the multiarch i386 C library (libc6:i386) next to the
# biarch one, a 32-bit test binary run with the path form and the bare names again; (b) where $LIB points for a
# 32-bit process: a stand-in 32-bit libgtk-nocsd.so.0 (dummy.c) placed in /usr/lib32 and in /usr/lib/i386-linux-gnu,
# each run with the path form; then the stand-ins are removed.
set -u
B=~/b1302
echo "== multiarch at $(date -u +%FT%TZ); foreign architectures: $(dpkg --print-foreign-architectures | xargs)"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q libc6:i386 > /tmp/i386.log 2>&1; echo "  apt-get install libc6:i386 rc=$?"
grep -E '^(Remov|Удал|The following packages will be REMOVED)' -A2 /tmp/i386.log | head -4 | sed 's/^/    /'
dpkg-query -W -f='  ${Package}:${Architecture} ${Version} ${Status}\n' libc6 libc6-i386 'libc6:i386' 2>/dev/null
ls -l /lib/ld-linux.so.2 /usr/lib/ld-linux.so.2 /usr/lib32/ld-linux.so.2 /usr/lib/i386-linux-gnu/ld-linux.so.2 2>&1 | sed 's/^/  /'
echo "  t32-biarch interpreter: $(readelf -l $B/t32-biarch | sed -n 's/.*interpreter: \(.*\)\]/\1/p')"
bash $B/i386.sh multiarch-installed $B/t32-biarch | sed 1d
echo "-- where \$LIB points: stand-in 32-bit libgtk-nocsd.so.0"
gcc -m32 -shared -fPIC -o /tmp/dummy32.so $B/dummy.c && echo "  dummy: $(file -b /tmp/dummy32.so | cut -d, -f1-2)"
for d in /usr/lib32 /usr/lib/i386-linux-gnu; do
  sudo install -m644 /tmp/dummy32.so $d/libgtk-nocsd.so.0
  echo "  stand-in only in $d:"
  LD_PRELOAD='/usr/$LIB/libgtk-nocsd.so.0' $B/t32-biarch 0 2>&1 | sed 's/^/    /'
  sudo rm -f -- "$d/libgtk-nocsd.so.0"
done
echo "  stand-ins removed: $(ls /usr/lib32/libgtk-nocsd.so.0 /usr/lib/i386-linux-gnu/libgtk-nocsd.so.0 2>&1 | grep -c 'No such\|Нет такого')/2 absent"
