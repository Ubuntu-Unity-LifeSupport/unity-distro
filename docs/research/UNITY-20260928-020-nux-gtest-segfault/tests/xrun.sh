#!/bin/bash
# xrun.sh N NORESET - gtest-nux-slow N times, each on a fresh dummy Xorg :55, with or without -noreset; count segfaults and server resets
cd /home/mike/b020/nux/tests
conf=/tmp/dummy55.conf
printf "Section \"Monitor\"\n Identifier \"M\"\nEndSection\nSection \"Device\"\n Identifier \"D\"\n Driver \"dummy\"\nEndSection\nSection \"Screen\"\n DefaultDepth 24\n Identifier \"S\"\n Device \"D\"\n Monitor \"M\"\nEndSection\n" > $conf
seg=0
for i in $(seq $1); do
  opt=""; [ "$2" = yes ] && opt=-noreset
  Xorg :55 -config $conf -logfile /tmp/xorg55-$i.log $opt > /dev/null 2>&1 & x=$!
  sleep 3
  DISPLAY=:55 LIBGL_ALWAYS_SOFTWARE=1 ./gtest-nux-slow > /tmp/xrun-$i.out 2>&1; rc=$?
  kill $x; wait $x 2>/dev/null
  resets=$(grep -c "Server terminated successfully\|^.*(II) Server terminated" /tmp/xorg55-$i.log)
  gen=$(grep -c "X.Org X Server\b\|Build Operating System" /tmp/xorg55-$i.log)
  [ $rc -ge 128 ] && seg=$((seg+1))
  echo "run $i noreset=$2: rc=$rc last=$(grep "^\[ RUN" /tmp/xrun-$i.out | tail -1 | cut -c14-) server-generations=$(grep -c "Current version of pixman" /tmp/xorg55-$i.log)"
done
echo "noreset=$2: segfaults $seg of $1"
