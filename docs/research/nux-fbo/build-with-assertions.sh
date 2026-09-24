#!/bin/sh
# build nux (NuxCore, NuxGraphics, Nux) with libstdc++ assertions, no install
set -e
cd /tmp/asrt/src
NOCONFIGURE=1 ./autogen.sh >/tmp/asrt/autogen.log 2>&1 || autoreconf -fi >/tmp/asrt/autogen.log 2>&1
./configure --disable-tests --disable-documentation CXXFLAGS="-O2 -g -D_GLIBCXX_ASSERTIONS" >/tmp/asrt/configure.log 2>&1
make -j4 >/tmp/asrt/make.log 2>&1
echo BUILD-OK
