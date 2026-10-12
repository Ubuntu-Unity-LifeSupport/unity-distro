#!/bin/bash
# devtests.sh STEP - UNITY-20261009-003/-004/-005: the new tests one by one, with their own --gtest_filter, on the
# control tree (the tests only, on +unity6) and on the fix tree (+unity7), built with the project's CMake on target2
# (a disposable test machine; the gated build is sbuild's). On +unity6 some new tests end in SIGSEGV, which ends the
# whole test binary; run one at a time, each one's outcome is visible.
#   setup   deb-src on, apt-get build-dep hud, the two trees from git archive tarballs in ~/b0309/dev
#   build   cmake + make in each tree
#   run     the new tests, each alone, in each tree
set -u
B=~/b0309/dev
export LANG=C.UTF-8
case $1 in
setup)
  touch ~/.dirty
  sudo sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources
  sudo apt-get update -q > /tmp/upd-src.log 2>&1; echo "update rc=$?"
  sudo DEBIAN_FRONTEND=noninteractive apt-get build-dep -y -q hud > /tmp/bd.log 2>&1; echo "build-dep rc=$?"
  grep -E "^E:" /tmp/bd.log | head -3
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q cmake dbus-x11 xvfb > /dev/null 2>&1; echo "extra rc=$?"
  for t in control fix; do rm -rf "${B:?}/$t"; mkdir -p $B/$t; tar -xf $B/$t.tar -C $B/$t; done
  echo "trees: $(ls $B)" ;;
build)
  for t in control fix; do
    rm -rf "${B:?}/$t-build"; mkdir -p $B/$t-build; cd $B/$t-build
    # the options of debian/rules, and the systemd user unit directory pkg-config would give (no systemd-dev here)
    cmake ../$t -DCMAKE_BUILD_TYPE=Debug -DENABLE_DOCUMENTATION=OFF -DENABLE_BAMF=ON \
      -DDEBIAN_TARGET_DIR=x86_64-linux-gnu -DSYSTEMD_USER_DIR=/usr/lib/systemd/user > $B/$t-cmake.log 2>&1; echo "$t cmake rc=$?"
    make -j4 > $B/$t-make.log 2>&1; echo "$t make rc=$? warnings $(grep -c 'warning:' $B/$t-make.log)"
    grep -E "error:" $B/$t-make.log | head -5
  done ;;
run)
  TESTS="test-integration-tests:TestHud.LegacyExecuteUsesItemTarget
    test-service-unit-tests:TestQuery.ExecuteCommandWithStructureKeyOutsideDBus
    test-service-unit-tests:TestQuery.ExecuteCommandWithNonNumericStringKey
    test-service-unit-tests:TestQuery.ExecuteCommandWithNumericStringKey
    test-service-unit-tests:TestQuery.ExecuteCommandWithoutFocusedWindow
    test-service-unit-tests:TestQuery.ExecuteCommandWithBadKeyOverDBus
    test-service-unit-tests:TestQuery.ExecuteParameterizedWithBadKeys
    test-service-unit-tests:TestQuery.ExecuteParameterizedWithoutFocusedWindow
    test-service-unit-tests:TestItemStore.ExecuteUnknownIdLeavesStoreUnchanged
    test-service-unit-tests:TestApplication.RelativeDataHomeIgnored
    test-qtgmenu-unit-tests:TestActivationParameter.*"
  for t in control fix; do
    echo "== $t"
    for x in $TESTS; do
      bin=${x%%:*}; filter=${x#*:}
      f=$(find $B/$t-build/tests -name $bin -type f -perm -u+x | head -1)
      if [ -z "$f" ]; then echo "  $filter: binary $bin not built"; continue; fi
      out=$(cd $(dirname $f) && timeout 120 xvfb-run -a dbus-run-session -- $f --gtest_filter="$filter" 2>&1); rc=$?
      res=$(echo "$out" | grep -E "^\[  (PASSED|FAILED)  \]|tests? ran" | tail -2 | tr '\n' ' ')
      [ -z "$res" ] && res="(no gtest summary: $(echo "$out" | grep -iE 'segmentation|signal|abort|No tests' | head -1))"
      echo "  $filter: rc=$rc $res"
    done
  done ;;
esac
