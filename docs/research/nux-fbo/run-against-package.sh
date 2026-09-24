#!/bin/sh
# fbo.cpp against the installed libnux (the package as shipped), no assertions
cd /tmp/asrt
g++ -std=c++17 -O0 -g fbo.cpp -o fbo-sys $(pkg-config --cflags --libs nux-4.0) 2>&1 | grep -v warning | head
ldd ./fbo-sys | grep -E 'libnux-graphics'
xvfb-run -a -s "-screen 0 1024x768x24" ./fbo-sys 2>&1 | grep -E 'attach|refs|texture|DONE|Assert'
echo "exit=$?"
