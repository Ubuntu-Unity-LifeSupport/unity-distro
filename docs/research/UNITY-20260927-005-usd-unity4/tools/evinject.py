#!/usr/bin/env python3
# Inject relative motion into an EXISTING evdev device (not XTEST, not uinput):
# writing input_event structs to /dev/input/eventN makes the kernel deliver
# them to every reader of that device, the X server's libinput included.
# usage: sudo evinject.py /dev/input/event4 [steps] [dx] [dy]
import struct, sys, time
dev = sys.argv[1]; steps = int(sys.argv[2]) if len(sys.argv) > 2 else 10
dx = int(sys.argv[3]) if len(sys.argv) > 3 else 5; dy = int(sys.argv[4]) if len(sys.argv) > 4 else 3
EV_SYN, EV_REL, REL_X, REL_Y = 0, 2, 0, 1
def ev(t, c, v):
    s = time.time(); return struct.pack("llHHi", int(s), int((s % 1) * 1e6), t, c, v)
with open(dev, "wb", buffering=0) as f:
    for i in range(steps):
        f.write(ev(EV_REL, REL_X, dx) + ev(EV_REL, REL_Y, dy) + ev(EV_SYN, 0, 0))
        time.sleep(0.02)
