#!/usr/bin/env python3
# Play a sequence of real mouse actions into an EXISTING relative evdev device
# (the PS/2 mouse): not XTEST. Known issue #3 (agent A).
# usage: sudo evseq.py /dev/input/eventN 'move 10 0' 'down left' 'wheel -1' 'up left' 'sleep 0.2' ...
import struct, sys, time
EV_SYN, EV_KEY, EV_REL = 0, 1, 2; REL_X, REL_Y, REL_WHEEL = 0, 1, 8
BTN = {"left": 0x110, "right": 0x111, "middle": 0x112}
def ev(t, c, v):
    s = time.time(); return struct.pack("llHHi", int(s), int((s % 1) * 1e6), t, c, v)
with open(sys.argv[1], "wb", buffering=0) as f:
    for cmd in sys.argv[2:]:
        a = cmd.split()
        if a[0] == "move":      # move DX DY [STEPS]
            n = int(a[3]) if len(a) > 3 else 1; dx, dy = int(a[1]) // n, int(a[2]) // n
            for _ in range(n):
                f.write(ev(EV_REL, REL_X, dx) + ev(EV_REL, REL_Y, dy) + ev(EV_SYN, 0, 0)); time.sleep(0.015)
        elif a[0] in ("down", "up"):
            f.write(ev(EV_KEY, BTN[a[1]], 1 if a[0] == "down" else 0) + ev(EV_SYN, 0, 0)); time.sleep(0.05)
        elif a[0] == "wheel":
            f.write(ev(EV_REL, REL_WHEEL, int(a[1])) + ev(EV_SYN, 0, 0)); time.sleep(0.05)
        elif a[0] == "sleep":
            time.sleep(float(a[1]))
