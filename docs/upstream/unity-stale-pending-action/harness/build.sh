#!/bin/sh
# Harness only, not part of the patch: googletest 1.17 needs C++17 while Unity
# asks for C++14, and GCC 15 makes incompatible-pointer-types an error in
# tests/gmockvolume.c.
set -e
cd /src
[ -e .harness-applied ] || { patch -p1 < /test.diff; patch -p1 < /fix.diff; sed -i 's/-std=c++14/-std=c++17/' CMakeLists.txt; touch .harness-applied; }
mkdir -p obj && cd obj
cmake .. -DCMAKE_C_FLAGS=-Wno-error=incompatible-pointer-types -DENABLE_UNIT_TESTS=ON -DENABLE_X_SUPPORT=ON -DCOMPIZ_BUILD_WITH_RPATH=FALSE -DCOMPIZ_PACKAGING_ENABLED=TRUE -DCOMPIZ_PLUGIN_INSTALL_TYPE=package > /cmake.log 2>&1
make -j4 test-gnome-session-manager
