#!/usr/bin/env python3
# Inject absolute motion into an existing evdev device (e.g. VirtualBox USB Tablet).
# usage: sudo evabs.py /dev/input/event5 [steps]
import struct, sys, time
dev = sys.argv[1]; steps = int(sys.argv[2]) if len(sys.argv) > 2 else 10
EV_SYN, EV_ABS, ABS_X, ABS_Y = 0, 3, 0, 1
def ev(t, c, v):
    s = time.time(); return struct.pack("llHHi", int(s), int((s % 1) * 1e6), t, c, v)
with open(dev, "wb", buffering=0) as f:
    for i in range(steps):
        f.write(ev(EV_ABS, ABS_X, 8000 + 300 * i) + ev(EV_ABS, ABS_Y, 9000 + 200 * i) + ev(EV_SYN, 0, 0))
        time.sleep(0.02)
