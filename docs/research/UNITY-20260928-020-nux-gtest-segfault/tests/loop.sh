#!/bin/bash
# loop.sh N BIN [FILTER] - run BIN N times under the dummy Xorg runner (as root, as Xorg needs), count segfaults, keep cores
cd ~/b020/nux/tests
sudo -n sysctl -q kernel.core_pattern=/tmp/core020.%e.%p
n=$1; bin=$2; f=${3:-*}; seg=0
for i in $(seq $n); do
  out=$(sudo -n bash -c "ulimit -c 0; ./dummy-xorg-test-runner.sh $bin --gtest_filter=\"$f\"" 2>&1); rc=$?
  last=$(echo "$out" | grep "^\[ RUN" | tail -1)
  if [ $rc -ge 128 ]; then seg=$((seg+1)); echo "run $i: rc=$rc SEGV in $last"; else echo "run $i: rc=$rc $(echo "$out" | grep -E "^\[  PASSED|^\[  FAILED  \] [0-9]" | tr "\n" " ")"; fi
done
echo "segfaults $seg of $n"; sudo -n ls /tmp/core020.* 2>/dev/null | head
