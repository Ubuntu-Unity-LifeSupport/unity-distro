#!/bin/sh
# compile fbo.cpp against the tree in /tmp/asrt/src and run it under Xvfb
cd /tmp/asrt
S=/tmp/asrt/src
CF=$(grep -E '^NUX_CFLAGS =' $S/Nux/Makefile | sed 's/^NUX_CFLAGS = //')
g++ -std=c++17 -O0 -g -D_GLIBCXX_ASSERTIONS -I$S $CF fbo.cpp -o fbo \
  -L$S/Nux/.libs -L$S/NuxGraphics/.libs -L$S/NuxCore/.libs \
  -lnux-4.0 -lnux-graphics-4.0 -lnux-core-4.0 \
  $(pkg-config --libs glib-2.0 sigc++-2.0 gl x11) 2>&1 | grep -v warning | head -20
export LD_LIBRARY_PATH=$S/Nux/.libs:$S/NuxGraphics/.libs:$S/NuxCore/.libs
export NUX_DATA_DIR=$S/data
ldd ./fbo | grep nux
xvfb-run -a -s "-screen 0 1024x768x24" ./fbo 2>&1 | grep -vE 'Gtk-|dbus|^$' | tail -15
echo "exit=$?"
