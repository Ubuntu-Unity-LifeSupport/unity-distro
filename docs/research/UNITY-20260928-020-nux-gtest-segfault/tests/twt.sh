#!/bin/bash
# twt.sh N - TestWindowThread.* N times on one dummy Xorg :55 -noreset, cores to /tmp/core020w.*
cd /home/mike/b020/nux/tests
sysctl -q kernel.core_pattern=/tmp/core020w.%p
ulimit -c unlimited
Xorg :55 -config /tmp/dummy55.conf -logfile /tmp/xorg55-twt.log -noreset > /dev/null 2>&1 & x=$!
sleep 3
seg=0
for i in $(seq $1); do
  DISPLAY=:55 LIBGL_ALWAYS_SOFTWARE=1 .libs/gtest-nux-slow --gtest_filter="TestWindowThread.*" > /tmp/twt-$i.out 2>&1; rc=$?
  [ $rc -ge 128 ] && { seg=$((seg+1)); echo "run $i rc=$rc last=$(grep "^\[ RUN" /tmp/twt-$i.out | tail -1 | cut -c14-)"; }
done
kill $x
echo "TestWindowThread only: segfaults $seg of $1"; ls /tmp/core020w.* 2>/dev/null | head -3
